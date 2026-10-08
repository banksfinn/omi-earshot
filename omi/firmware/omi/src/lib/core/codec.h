#ifndef CODEC_H
#define CODEC_H
#include <zephyr/kernel.h>

// Callback. capture_uptime_ms is k_uptime_get() at the frame's first sample.
typedef void (*codec_callback)(uint8_t *data, size_t len, int64_t capture_uptime_ms);
void set_codec_callback(codec_callback callback);

// Integration

int codec_receive_pcm(int16_t *data, size_t len);

/**
 * @brief Initialize the Codec
 *
 * Initializes the codec
 *
 * @return 0 if successful, negative errno code if error
 */
int codec_start();

#endif