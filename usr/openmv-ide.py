#!/usr/bin/env python2
import openmv
import gtk
import gobject
import pango
import serial
import platform
import sys, os, os.path
from time import sleep
from os.path import expanduser
import gtksourceview2 as gtksourceview
from glob import glob
import urllib2, json

#import pydfu on Linux
if platform.system() == "Linux":
    import pydfu

try:
    # 3.x name
    import configparser
except ImportError:
    # 2.x name
    configparser = __import__("ConfigParser")

if hasattr(sys,"frozen"):
    IDE_DIR=os.path.dirname(sys.executable)
    BUNDLE_DIR = sys._MEIPASS
else:
    IDE_DIR=os.path.dirname(os.path.realpath(__file__))
    BUNDLE_DIR = IDE_DIR

FIRMWARE_VERSION_MAJOR  = 1
FIRMWARE_VERSION_MINOR  = 1
FIRMWARE_VERSION_PATCH  = 0

DATA_DIR     = os.path.join(os.path.expanduser("~"), "openmv") #use home dir
SCRIPTS_DIR  = os.path.join(DATA_DIR, "scripts")
EXAMPLES_DIR = os.path.join(IDE_DIR, "examples")
GLADE_PATH   = os.path.join(BUNDLE_DIR, "openmv-ide.glade")
CONFIG_PATH  = os.path.join(DATA_DIR, "openmv.config")
UDEV_PATH    = "/etc/udev/rules.d/50-openmv.rules"

SCALE =1
RECENT_FILES_LIMIT=5
FLASH_OFFSETS= [0x08000000, 0x08004000, 0x08008000, 0x0800C000,
                0x08010000, 0x08020000, 0x08040000, 0x08060000,
                0x08080000, 0x080A0000, 0x080C0000, 0x080E0000]

DEFAULT_CONFIG='''\
[main]
board = OpenMV2
serial_port = /dev/openmvcam
recent =
last_fw_path =
baudrate = 921600
'''
RELEASE_TAG_NAME = 'v1.1'
RELEASE_URL = 'https://api.github.com/repos/openmv/openmv/releases/latest'

class OMVGtk:
    def __init__(self):
        #Set the Glade file
        self.builder = gtk.Builder()
        self.builder.add_from_file(GLADE_PATH)

        # get top window
        self.window = self.builder.get_object("top_window")

        # status bar stuff
        self.statusbar = self.builder.get_object("statusbar")
        self.statusbar_ctx = self.statusbar.get_context_id("default")

        # set buttons
        self.save_button = self.builder.get_object('save_file_toolbutton')
        self.connect_button = self.builder.get_object('connect_button')

        self.save_button.set_sensitive(False)
        self.connect_button.set_sensitive(True)

        # set control buttons
        self.controls = [
            self.builder.get_object('reset_button'),
            self.builder.get_object('bootloader_button'),
            self.builder.get_object('exec_button'),
            self.builder.get_object('stop_button'),
            self.builder.get_object('zoomin_button'),
            self.builder.get_object('zoomout_button'),
            self.builder.get_object('bestfit_button'),
            self.builder.get_object('refresh_button')]

        self.connected = False
        map(lambda x:x.set_sensitive(False), self.controls)

        # Disable dfu button on Windows
        if platform.system() == "Windows":
            self.controls.pop(1)

        # gtksourceview widget
        sourceview = gtksourceview.View()
        lang_manager = gtksourceview.language_manager_get_default()
        style_manager = gtksourceview.style_scheme_manager_get_default()

        # append cwd to style search paths
        style_manager.set_search_path(style_manager.get_search_path() +
                [os.path.join(IDE_DIR, "share/gtksourceview-2.0/styles")])

        # append cwd to language search paths
        lang_manager.set_search_path(lang_manager.get_search_path() +
                [os.path.join(IDE_DIR, "share/gtksourceview-2.0/language-specs")])

        # configure gtksourceview widget
        sourceview.set_show_line_numbers(True)
        sourceview.set_tab_width(4)
        sourceview.set_indent_on_tab(True)
        sourceview.set_insert_spaces_instead_of_tabs(True)
        sourceview.set_auto_indent(True)
        sourceview.set_highlight_current_line(True)

        # configure gtksourceview buffer
        self.buffer = gtksourceview.Buffer()
        self.buffer.set_highlight_syntax(True)
        self.buffer.set_language(lang_manager.get_language("python"))
        self.buffer.connect("changed", self.text_changed)

        sourceview.set_buffer(self.buffer)
        self.builder.get_object("src_scrolledwindow").add(sourceview)

        # Configure terminal window
        self.terminal_scroll = self.builder.get_object('vte_scrolledwindow')
        self.terminal = self.builder.get_object('vte_textview')
        self.terminal.modify_base(gtk.STATE_NORMAL, gtk.gdk.color_parse('black'))
        self.terminal.modify_text(gtk.STATE_NORMAL, gtk.gdk.color_parse('green'))

        # get drawingarea
        self.pixbuf = None
        self.drawingarea = self.builder.get_object("drawingarea")
        self.da_menu = self.builder.get_object("da_menu")

        # selection coords
        self.sel_ended=False
        self.selection_started=False
        self.x1 = self.y1 = self.x2 = self.y2 =0

        # set control scales attributes
        self.builder.get_object("contrast_adjust").attr=    openmv.ATTR_CONTRAST
        self.builder.get_object("brightness_adjust").attr=  openmv.ATTR_BRIGHTNESS
        self.builder.get_object("saturation_adjust").attr=  openmv.ATTR_SATURATION
        self.builder.get_object("gainceiling_adjust").attr= openmv.ATTR_GAINCEILING

        #connect signals
        signals = {
            "on_top_window_destroy"         : self.quit,
            "on_connect_clicked"            : self.connect_clicked,
            "on_reset_clicked"              : self.reset_clicked,
            "on_fwupdate_clicked"           : self.fwupdate_clicked,
            "on_fwpath_clicked"             : self.fwpath_clicked,
            "on_execute_clicked"            : self.execute_clicked,
            "on_stop_clicked"               : self.stop_clicked,
            "on_motion_notify"              : self.motion_notify,
            "on_button_press"               : self.button_pressed,
            "on_button_release"             : self.button_released,
            "on_open_file"                  : self.open_file,
            "on_new_file"                   : self.new_file,
            "on_save_file"                  : self.save_file,
            "on_save_file_as"               : self.save_file_as,
            "on_about_dialog"               : self.about_dialog,
            "on_pinout_dialog"              : self.pinout_dialog,
            "on_save_template_activate"     : self.save_template,
            "on_save_descriptor_activate"   : self.save_descriptor,
            "on_ctrl_scale_value_changed"   : self.on_ctrl_scale_value_changed,
            "on_zoomin_clicked"             : self.zoomin_clicked,
            "on_zoomout_clicked"            : self.zoomout_clicked,
            "on_bestfit_clicked"            : self.bestfit_clicked,
            "on_preferences_clicked"        : self.preferences_clicked,
            "on_updatefb_clicked"           : self.updatefb_clicked,
            "on_vte_size_allocate"          : self.scroll_terminal,
        }
        self.builder.connect_signals(signals)

        # create data directory
        if not os.path.isdir(DATA_DIR):
            os.makedirs(DATA_DIR)

        # create user scripts directory
        if not os.path.isdir(SCRIPTS_DIR):
            os.makedirs(SCRIPTS_DIR)

        # create fresh config if needed
        if not os.path.isfile(CONFIG_PATH):
            try:
                with open(CONFIG_PATH, "w") as f:
                    f.write(DEFAULT_CONFIG)
            except Exception as e:
                print ("Failed to create config file %s"%(e))
                sys.exit(1)

        # load config
        self.config = configparser.ConfigParser()
        try:
            self.config.read(CONFIG_PATH)
        except Exception as e:
            print ("Failed to open config file %s"%(e))
            sys.exit(1)

        # current file path
        self.file_path= None
        self.fw_file_path=""
        path = self.config.get("main", "last_fw_path")
        if os.path.isfile(path):
            self.fw_file_path = path

        # built-in examples menu
        submenu = gtk.Menu()
        menu = self.builder.get_object('example_menu')
        files = sorted(os.listdir(EXAMPLES_DIR))
        for f in files:
            if f.endswith(".py"):
                label = os.path.basename(f)
                mitem = gtk.MenuItem(label, use_underline=False)
                mitem.connect("activate", self.open_example, EXAMPLES_DIR)
                submenu.append(mitem)

        menu.set_submenu(submenu)

        # recent files menu
        self.files = []
        files =self.config.get("main", "recent")
        if files:
            self.files = files.split(',')
            self.update_recent_files()

        self.baudrate = int(self.config.get("main", "baudrate"))

        # load helloworld.py
        self._load_file(os.path.join(EXAMPLES_DIR, "helloworld.py"))

    def show_message_dialog(self, msg_type, msg):
        message = gtk.MessageDialog(parent=self.window, flags=gtk.DIALOG_DESTROY_WITH_PARENT,
                                    type=msg_type, buttons=gtk.BUTTONS_OK, message_format=msg)
        message.run()
        message.destroy()

    def refresh_gui(self, delay=0.0001, wait=0.0001):
        sleep(delay)
        gtk.main_iteration_do(block=False)
        sleep(wait)

    def connect(self):
        try:
            # opens CDC port.
            openmv.init(self.config.get("main", "serial_port"), baudrate=self.baudrate, timeout=0.3)
        except Exception as e:
            # create fresh config if needed
            if platform.system() == "Linux" and not os.path.isfile(UDEV_PATH):
                error_msg = ("Failed to open serial port.\n"
                             "Please install OpenMV's udev rules first:\n\n"
                             "sudo cp openmv/udev/50-openmv.rules /etc/udev/rules.d/\n"
                             "sudo udevadm control --reload-rules\n\n")
            else:
                error_msg = ("Failed to open serial port.\n"
                             "Please check the preferences Dialog.\n")

            self.show_message_dialog(gtk.MESSAGE_ERROR,"%s%s"%(error_msg, e))

            return

        # add terminal update callback
        gobject.gobject.timeout_add(10, omvgtk.update_terminal)

        # check firmware version
        fw_ver = openmv.fw_version()
        print("fw_version:" + str(fw_ver))
        if (fw_ver[0] != FIRMWARE_VERSION_MAJOR):
            self.show_message_dialog(gtk.MESSAGE_ERROR, "Firmware version mismatch! Please upgrade the firmware")
            return

        # interrupt any running code
        openmv.stop_script()

        self.connected = True
        self._update_title()
        self.connect_button.set_sensitive(False)
        map(lambda x:x.set_sensitive(True), self.controls)

    def disconnect(self):
        try:
            # stop running code
            openmv.stop_script();
        except:
            pass

        self.connected = False
        self._update_title()
        self.connect_button.set_sensitive(True)
        map(lambda x:x.set_sensitive(False), self.controls)

    def connect_clicked(self, widget):
        self.connect()

    def fwpath_clicked(self, widget):
        fw_entry = self.builder.get_object("fw_entry")
        dialog = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_current_folder(SCRIPTS_DIR)
        ff = gtk.FileFilter()
        ff.set_name("dfu")
        ff.add_pattern("*.bin") #TODO change to DFU
        dialog.add_filter(ff)

        if dialog.run() == gtk.RESPONSE_OK:
            fw_entry.set_text(dialog.get_filename())

        dialog.destroy()

    # Fake multitasking :P
    def fwupdate_task(self, state):
        if (state["init"]):
            pydfu.init()
            state["init"]=False
            state["erase"]=True
            state["bar"].set_text("Erasing...")
            return True
        elif (state["erase"]):
            page = state["page"]
            total = len(FLASH_OFFSETS)
            pydfu.page_erase(FLASH_OFFSETS[page])
            page +=1
            state["bar"].set_fraction(page/float(total))
            if (page == total):
                state["erase"] = False
                state["write"] = True
                state["bar"].set_text("Uploading...")
            state["page"] = page
            return True
        elif (state["write"]):
            buf = state["buf"]
            xfer_bytes = state["xfer_bytes"]
            xfer_total = state["xfer_total"]

            # Send chunk
            chunk = min (64, xfer_total-xfer_bytes)
            pydfu.write_page(buf[xfer_bytes:xfer_bytes+chunk], xfer_bytes)

            xfer_bytes += chunk
            state["xfer_bytes"] = xfer_bytes
            state["bar"].set_fraction(xfer_bytes/float(xfer_total))

            if (xfer_bytes == xfer_total):
                pydfu.exit_dfu()
                state["dialog"].hide()
                return False

            return True

    def fwupdate_clicked(self, widget):
        if (self.connected):
            dialog = self.builder.get_object("fw_dialog")
            fw_entry = self.builder.get_object("fw_entry")
            fw_progress = self.builder.get_object("fw_progressbar")
            ok_button = self.builder.get_object("fw_ok_button")
            cancel_button = self.builder.get_object("fw_cancel_button")

            ok_button.set_sensitive(True)
            cancel_button.set_sensitive(True)
            dialog.set_transient_for(self.window);

            # default FW bin path
            fw_entry.set_text(self.fw_file_path)
            fw_progress.set_text("")
            fw_progress.set_fraction(0.0)

            if dialog.run() == gtk.RESPONSE_OK:
                ok_button.set_sensitive(False)
                cancel_button.set_sensitive(False)

                fw_path = fw_entry.get_text()
                try:
                    with open(fw_path, 'r') as f:
                        buf= f.read()
                except Exception as e:
                    dialog.hide()
                    self.show_message_dialog(gtk.MESSAGE_ERROR, "Failed to open file %s"%str(e))
                    return

                self.fw_file_path = fw_path
                self.config.set("main", "last_fw_path", fw_path)

                state={"init":True, "erase":False, "write":False,
                    "page":0, "buf":buf, "bar":fw_progress, "dialog":dialog,
                    "xfer_bytes":0, "xfer_total":len(buf)}

                # call dfu-util
                openmv.enter_dfu()
                sleep(1.0)
                gobject.gobject.idle_add(self.fwupdate_task, state)
            else:
                dialog.hide()

    def reset_clicked(self, widget):
        if (self.connected):
            openmv.reset()

    def execute_clicked(self, widget):
        buf = self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter())
        # exec script
        openmv.exec_script(buf)

    def stop_clicked(self, widget):
        openmv.stop_script();

    def zoomin_clicked(self, widget):
        global SCALE
        SCALE+=1

    def zoomout_clicked(self, widget):
        global SCALE
        if SCALE>1:
            SCALE-=1

    def bestfit_clicked(self, widget):
        global SCALE
        SCALE=1

    def preferences_clicked(self, widget):
        board_combo = self.builder.get_object("board_combo")
        sport_combo = self.builder.get_object("sport_combo")
        baud_combo = self.builder.get_object("baud_combo")
        dialog = self.builder.get_object("preferences_dialog")

        # Fill serial ports combo
        sport_combo.get_model().clear()
        serial_ports = self.list_serial_ports()
        for i in serial_ports:
            sport_combo.append_text(i)

        if len(serial_ports):
            sport_combo.set_active(0)

        # Save config
        if dialog.run() == gtk.RESPONSE_OK:
            self.config.set("main", "board", board_combo.get_active_text())
            self.config.set("main", "serial_port", sport_combo.get_active_text())
            self.config.set("main", "baudrate", baud_combo.get_active_text())
            self.save_config()

        dialog.hide()

    def updatefb_clicked(self, widget):
        openmv.fb_update()

    def button_pressed(self, widget, event):
        self.x1 = int(event.x)
        self.y1 = int(event.y)
        self.x2 = int(event.x)
        self.y2 = int(event.y)
        self.selection_started = True

    def button_released(self, widget, event):
        self.x2 = int(event.x)
        self.y2 = int(event.y)
        self.selection_started = False
        if (self.connected):
            self.da_menu.popup(None, None, None, event.button, event.time, None)
            self.da_menu.show_all()

    def motion_notify(self, widget, event):
        x = int(event.x)
        y = int(event.y)
        self.x2 = int(event.x)
        self.y2 = int(event.y)
        if self.pixbuf and x < self.pixbuf.get_width() and y < self.pixbuf.get_height():
            pixel = self.pixbuf.get_pixels_array()[y][x]
            rgb = "(%d, %d, %d)" %(pixel[0], pixel[1], pixel[2])
            self.statusbar.pop(self.statusbar_ctx)
            self.statusbar.push(self.statusbar_ctx, rgb)

    def scroll_terminal(self, widget, event):
        adj = self.terminal_scroll.get_vadjustment()
        adj.set_value(adj.upper - adj.page_size)

    def update_terminal(self):
        try:
            buf_len = openmv.tx_buf_len()
            if (buf_len):
                buf = openmv.tx_buf(buf_len)
                buffer = self.terminal.get_buffer()
                buffer.insert(buffer.get_end_iter(), buf)
        except:
            pass

        return True

    def update_drawing(self):
        if (not self.connected):
            return True

        try:
            # read drawingarea
            fb = openmv.fb_dump()
        except Exception as e:
            self.disconnect()
            self._update_title()
            return True

        if fb:
            # create pixbuf from np array
            self.pixbuf = gtk.gdk.pixbuf_new_from_array(fb[2], gtk.gdk.COLORSPACE_RGB, 8)
            self.pixbuf = self.pixbuf.scale_simple(fb[0]*SCALE, fb[1]*SCALE, gtk.gdk.INTERP_BILINEAR)

            self.drawingarea.realize();
            cm = self.drawingarea.window.get_colormap()
            gc = self.drawingarea.window.new_gc(foreground=cm.alloc_color('#FFFFFF',True,False))

            self.drawingarea.set_size_request(fb[0]*SCALE, fb[1]*SCALE)
            self.drawingarea.window.draw_pixbuf(gc, self.pixbuf, 0, 0, 0, 0)
            if self.selection_started or self.da_menu.flags() & gtk.MAPPED:
                self.drawingarea.window.draw_rectangle(gc, False, self.x1, self.y1, self.x2-self.x1, self.y2-self.y1)

        return True


    def on_ctrl_scale_value_changed(self, adjust):
        openmv.set_attr(adjust.attr, int(adjust.value))

    def save_config(self):
        # config.set("section", "key", value)
        self.config.set("main", "recent", ','.join(self.files))
        with open(CONFIG_PATH, "w") as file:
           self.config.write(file)

    def _update_title(self):
        if (self.file_path==None):
            title = "Untitled"
        else:
            title = os.path.basename(self.file_path)

        title += " [Connected]" if self.connected else " [Disconnected]"
        self.window.set_title(title)


    def update_recent_files(self):
        if (self.file_path and self.file_path not in self.files ):
            self.files.insert(0, self.file_path)

        if len(self.files)>RECENT_FILES_LIMIT:
            self.files.pop()

        submenu = gtk.Menu()
        menu = self.builder.get_object('recent_menu')
        for f in self.files:
            if f.endswith(".py"):
                mitem =gtk.MenuItem(f, use_underline=False)
                mitem.connect("activate", self.open_example, "")
                submenu.append(mitem)

        menu.set_submenu(submenu)
        menu.show_all()

    def _load_file(self, path):
        self.file_path = path
        if path == None: # New file
            self.save_button.set_sensitive(True)
            self.buffer.set_text("")
        else:
            self.save_button.set_sensitive(False)
            with open(path, "r") as file:
                self.buffer.set_text(file.read())
            self.update_recent_files()
        self._update_title()

    def _save_file(self, new_file):
        if new_file:
            dialog = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_SAVE,
                    buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
            dialog.set_default_response(gtk.RESPONSE_OK)
            dialog.set_current_folder(SCRIPTS_DIR)
            ff = gtk.FileFilter()
            ff.set_name("python")
            ff.add_pattern("*.py")
            dialog.add_filter(ff)

            if dialog.run() == gtk.RESPONSE_OK:
                self.file_path = dialog.get_filename()
                self.save_button.set_sensitive(False)
                self._update_title()
                self.update_recent_files()

                # append .py
                filename = dialog.get_filename()
                if not filename.endswith(".py"):
                    filename += ".py"

                # save file
                with open(filename, "w") as file:
                    file.write(self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter()))

            dialog.destroy()
        else:
            self.save_button.set_sensitive(False)
            with open(self.file_path, "w") as file:
                file.write(self.buffer.get_text(self.buffer.get_start_iter(), self.buffer.get_end_iter()))

    def save_template(self, widget):
        self.da_menu.hide()
        x = self.x1
        y = self.y1
        w = self.x2-self.x1
        h = self.y2-self.y1

        entry = self.builder.get_object("template_entry")
        image = self.builder.get_object("template_image")
        image.set_from_pixbuf(self.pixbuf.subpixbuf(x, y, w, h))

        dialog = self.builder.get_object("save_template_dialog")
        dialog.set_transient_for(self.window);
        #dialog.set_default_response(gtk.RESPONSE_OK)

        if dialog.run() == gtk.RESPONSE_OK:
            openmv.save_template(x/SCALE, y/SCALE, w/SCALE, h/SCALE, entry.get_text()) #Use Scale
        dialog.hide()

    def save_descriptor(self, widget):
        self.da_menu.hide()
        x = self.x1
        y = self.y1
        w = self.x2-self.x1
        h = self.y2-self.y1

        entry = self.builder.get_object("desc_entry")
        image = self.builder.get_object("desc_image")
        image.set_from_pixbuf(self.pixbuf.subpixbuf(x, y, w, h))

        dialog = self.builder.get_object("save_descriptor_dialog")
        dialog.set_transient_for(self.window);
        #dialog.set_default_response(gtk.RESPONSE_OK)

        if dialog.run() == gtk.RESPONSE_OK:
            #if not entry.get_text():
            openmv.save_descriptor(x/SCALE, y/SCALE, w/SCALE, h/SCALE, entry.get_text()) #Use Scale
        dialog.hide()

    def new_file(self, widget):
        self._load_file(None)

    def save_file(self, widget):
        self._save_file(self.file_path==None)

    def save_file_as(self, widget):
        self._save_file(True)

    def open_file(self, widget):
        dialog = gtk.FileChooserDialog(title=None,action=gtk.FILE_CHOOSER_ACTION_OPEN,
                buttons=(gtk.STOCK_CANCEL, gtk.RESPONSE_CANCEL, gtk.STOCK_OPEN, gtk.RESPONSE_OK))
        dialog.set_default_response(gtk.RESPONSE_OK)
        dialog.set_current_folder(SCRIPTS_DIR)
        ff = gtk.FileFilter()
        ff.set_name("python")
        ff.add_pattern("*.py")
        dialog.add_filter(ff)

        if dialog.run() == gtk.RESPONSE_OK:
            self._load_file(dialog.get_filename())

        dialog.destroy()

    def open_example(self, widget, basedir):
        self.file_path = os.path.join(basedir, widget.get_label())
        self._load_file(self.file_path)

    def about_dialog(self, widget):
        dialog = self.builder.get_object("about_dialog")
        dialog.run()
        dialog.hide()

    def pinout_dialog(self, widget):
        dialog = self.builder.get_object("pinout_dialog")
        dialog.run()
        dialog.hide()

    def text_changed(self, widget):
        self.save_button.set_sensitive(True)

    def list_serial_ports(self):
        serial_ports = []
        system_name = platform.system()

        if system_name == "Linux":
            serial_ports.append("/dev/openmvcam")
        elif system_name == "Darwin":
            serial_ports.extend(glob('/dev/tty.*'))
        elif system_name == "Windows":
            for i in range(256):
                try:
                    port = "COM%d"%i
                    s = serial.Serial(port)
                    serial_ports.append(port)
                    s.close()
                except serial.SerialException:
                    pass

        return serial_ports

    def check_for_updates(self):
        try:
            url = urllib2.urlopen(RELEASE_URL)
            release = json.loads(url.read())
            url.close()
            if (release['tag_name'] != RELEASE_TAG_NAME):
                dialog = self.builder.get_object("update_dialog")
                dn_button = self.builder.get_object("download_button")

                # Set release notes
                self.builder.get_object("rn_label").\
                set_text('Release notes (%s):\n\n%s'%(release['tag_name'], release['body']))
                # Set URL
                dn_button.set_uri(release['html_url'])
                dialog.run()
                dialog.hide()
        except:
            pass #pass quietly

    def quit(self, widget):
        try:
            # disconnect
            self.disconnect()
        except:
            pass

        self.save_config()
        # exit
        gtk.main_quit()

if __name__ == "__main__":
    omvgtk = OMVGtk()
    omvgtk.window.show_all()
    omvgtk.check_for_updates()
    gobject.gobject.timeout_add(30, omvgtk.update_drawing)
    gtk.main()
