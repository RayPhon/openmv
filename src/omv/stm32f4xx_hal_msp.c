/*
 * This file is part of the OpenMV project.
 * Copyright (c) 2013/2014 Ibrahim Abdelkader <i.abdalkader@gmail.com>
 * This work is licensed under the MIT license, see the file LICENSE for details.
 *
 * HAL MSP.
 *
 */
#include <stm32f4xx_hal.h>
#include <stm32f4xx_hal_msp.h>
/* GPIO struct */
typedef struct {
    GPIO_TypeDef *port;
    uint16_t pin;
} gpio_t;

/* DCMI GPIOs */
static const gpio_t dcmi_pins[] = {
    {DCMI_D0_PORT, DCMI_D0_PIN},
    {DCMI_D1_PORT, DCMI_D1_PIN},
    {DCMI_D2_PORT, DCMI_D2_PIN},
    {DCMI_D3_PORT, DCMI_D3_PIN},
    {DCMI_D4_PORT, DCMI_D4_PIN},
    {DCMI_D5_PORT, DCMI_D5_PIN},
    {DCMI_D6_PORT, DCMI_D6_PIN},
    {DCMI_D7_PORT, DCMI_D7_PIN},
    {DCMI_HSYNC_PORT, DCMI_HSYNC_PIN},
    {DCMI_VSYNC_PORT, DCMI_VSYNC_PIN},
    {DCMI_PXCLK_PORT, DCMI_PXCLK_PIN},
};

#define NUM_DCMI_PINS   (sizeof(dcmi_pins)/sizeof(dcmi_pins[0]))

void SystemClock_Config(void);

void HAL_MspInit(void)
{
    /* Set the system clock */
    SystemClock_Config();

    /* Config Systick */
    HAL_NVIC_SetPriority(SysTick_IRQn, 0, 0);

    /* Enable GPIO clocks */
    __GPIOA_CLK_ENABLE();
    __GPIOB_CLK_ENABLE();
    __GPIOC_CLK_ENABLE();
    __GPIOD_CLK_ENABLE();
    __GPIOE_CLK_ENABLE();
#ifdef OPENMV2
    __GPIOF_CLK_ENABLE();
    __GPIOG_CLK_ENABLE();
#endif

    /* Enable DMA clocks */
    __DMA2_CLK_ENABLE();

    /* Conigure DCMI GPIO */
    GPIO_InitTypeDef  GPIO_InitStructure;
    GPIO_InitStructure.Pull  = GPIO_PULLDOWN;
    GPIO_InitStructure.Speed = GPIO_SPEED_LOW;
    GPIO_InitStructure.Mode  = GPIO_MODE_OUTPUT_PP;

    GPIO_InitStructure.Pin = DCMI_RESET_PIN;
    HAL_GPIO_Init(DCMI_RESET_PORT, &GPIO_InitStructure);

    GPIO_InitStructure.Pin = DCMI_PWDN_PIN;
    HAL_GPIO_Init(DCMI_PWDN_PORT, &GPIO_InitStructure);

    /* Configure SD CD PIN */
    GPIO_InitStructure.Pin      = SD_CD_PIN;
    GPIO_InitStructure.Pull     = GPIO_NOPULL;
    GPIO_InitStructure.Speed    = GPIO_SPEED_LOW;
    GPIO_InitStructure.Mode     = GPIO_MODE_INPUT;
    HAL_GPIO_Init(SD_CD_PORT, &GPIO_InitStructure);
}

void HAL_I2C_MspInit(I2C_HandleTypeDef *hi2c)
{
    if (hi2c->Instance == SCCB_I2C) {
        /* Enable I2C clock */
        SCCB_CLK_ENABLE();

        /* Configure SCCB GPIOs */
        GPIO_InitTypeDef GPIO_InitStructure;
        GPIO_InitStructure.Pull      = GPIO_NOPULL;
        GPIO_InitStructure.Speed     = GPIO_SPEED_LOW;
        GPIO_InitStructure.Mode      = GPIO_MODE_AF_OD;
        GPIO_InitStructure.Alternate = SCCB_AF;

        GPIO_InitStructure.Pin = SCCB_SCL_PIN;
        HAL_GPIO_Init(SCCB_PORT, &GPIO_InitStructure);

        GPIO_InitStructure.Pin = SCCB_SDA_PIN;
        HAL_GPIO_Init(SCCB_PORT, &GPIO_InitStructure);
    }
}

void HAL_I2C_MspDeInit(I2C_HandleTypeDef *hi2c)
{
    if (hi2c->Instance == SCCB_I2C) {
        SCCB_CLK_DISABLE();
    }
}

void HAL_TIM_PWM_MspInit(TIM_HandleTypeDef *htim)
{
    if (htim->Instance == DCMI_TIM) {
        /* Enable DCMI timer clock */
        DCMI_TIM_CLK_ENABLE();

        /* Timer GPIO configuration */
        GPIO_InitTypeDef  GPIO_InitStructure;
        GPIO_InitStructure.Pin       = DCMI_TIM_PIN;
        GPIO_InitStructure.Pull      = GPIO_NOPULL;
        GPIO_InitStructure.Speed     = GPIO_SPEED_LOW;
        GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
        GPIO_InitStructure.Alternate = DCMI_TIM_AF;
        HAL_GPIO_Init(DCMI_TIM_PORT, &GPIO_InitStructure);
    }
}

void HAL_DCMI_MspInit(DCMI_HandleTypeDef* hdcmi)
{
    /* DCMI clock enable */
    __DCMI_CLK_ENABLE();

    /* DCMI GPIOs configuration */
    GPIO_InitTypeDef  GPIO_InitStructure;
    GPIO_InitStructure.Pull      = GPIO_PULLDOWN;
    GPIO_InitStructure.Speed     = GPIO_SPEED_LOW;
    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Alternate = GPIO_AF13_DCMI;

    for (int i=0; i<NUM_DCMI_PINS; i++) {
        GPIO_InitStructure.Pin = dcmi_pins[i].pin;
        HAL_GPIO_Init(dcmi_pins[i].port, &GPIO_InitStructure);
    }
}

#ifdef OPENMV1
void HAL_SPI_MspInit(SPI_HandleTypeDef *hspi)
{
    GPIO_InitTypeDef GPIO_InitStructure;
    if (hspi->Instance == SD_SPI) {
            /* Enable clock */
            SD_SPI_CLK_ENABLE();

            /* Configure SPI GPIOs */
            GPIO_InitStructure.Pull      = GPIO_NOPULL;
            GPIO_InitStructure.Speed     = GPIO_SPEED_MEDIUM;
            GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
            GPIO_InitStructure.Alternate = SD_SPI_AF;

            GPIO_InitStructure.Pin = SD_MOSI_PIN;
            HAL_GPIO_Init(SD_MOSI_PORT, &GPIO_InitStructure);

            GPIO_InitStructure.Pin = SD_MISO_PIN;
            HAL_GPIO_Init(SD_MISO_PORT, &GPIO_InitStructure);

            GPIO_InitStructure.Pin = SD_SCLK_PIN;
            HAL_GPIO_Init(SD_SCLK_PORT, &GPIO_InitStructure);

            GPIO_InitStructure.Pin = SD_CS_PIN;
            GPIO_InitStructure.Mode = GPIO_MODE_OUTPUT_PP;
            HAL_GPIO_Init(SD_CS_PORT, &GPIO_InitStructure);

            /* De-select the Card: Chip Select high */
            SD_DESELECT();

    }
}
#endif

#ifdef OPENMV2
void HAL_SD_MspInit(SD_HandleTypeDef *hsd)
{
    /* Enable SDIO clock */
    __SDIO_CLK_ENABLE();

    /* SDIO GPIOs configuration */
    GPIO_InitTypeDef  GPIO_InitStructure;
    GPIO_InitStructure.Pull      = GPIO_NOPULL;
    GPIO_InitStructure.Speed     = GPIO_SPEED_MEDIUM;
    GPIO_InitStructure.Mode      = GPIO_MODE_AF_PP;
    GPIO_InitStructure.Alternate = GPIO_AF12_SDIO;

    /* SDIO_D0..D3, SDIO_CLK */
    GPIO_InitStructure.Pin       = GPIO_PIN_8|GPIO_PIN_9|GPIO_PIN_10|GPIO_PIN_11|GPIO_PIN_12;
    HAL_GPIO_Init(GPIOC, &GPIO_InitStructure);

    /* SDIO_CMD */
    GPIO_InitStructure.Pin       = GPIO_PIN_2;
    HAL_GPIO_Init(GPIOD, &GPIO_InitStructure);
}

void HAL_SD_MspDeInit(SD_HandleTypeDef *hsd)
{
    __SDIO_CLK_DISABLE();
}
#endif //OPENMV2

void HAL_MspDeInit(void)
{

}
