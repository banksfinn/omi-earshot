# Pocket weak-link pendant firmware

Prepared for estate #4932 on 2026-10-25. Nothing has been flashed. Pocket has not been changed or rebuilt. Finn performs the update from Pocket after the pocket resident chooses and bundles the image.

## Images and source

The source baseline is commit `1dac191934e40378159a1c03bd4ff0b478875a43` on `pendant-no-loss`. The checkout was clean. It builds DIS (Bluetooth Device Information Service) revision `3.0.29`. The old build was made just before that commit was recorded. Rebuilding that source reproduced the original executable payload and image header byte for byte. Pocket's existing bundled `omi.signed.bin` also equals the saved original signed image. These establish a reproducible source baseline for the local image. The pendant itself was not read back; its reported `3.0.29` version is supplied by Finn, not independently verified here.

All preserved files are under `images/2026-10-25/` in this repository:

| Folder | Bluetooth version | MCUboot image version | Purpose |
| --- | --- | --- | --- |
| `stock-3.0.29` | `3.0.29` | `0.0.0+0` | Original zip and both merged hex files, copied before building |
| `weaklink-3.0.30` | `3.0.30-weaklink` | `3.0.30+0` | Custom update |
| `rollback-3.0.31-stock` | `3.0.31` | `3.0.31+0` | Stock behavior, with higher version numbers for recovery |

Each folder contains `dfu_application.zip`, extracted `omi.signed.bin`, `merged.hex`, `merged_CPUNET.hex`, and `SHA256SUMS`. Verify a folder with `shasum -a 256 -c SHA256SUMS` inside that folder. See `images/2026-10-25/verification.txt` for signature checks and payload comparisons. The build output at `omi/firmware/v2.9.0/build/dfu_application.zip` is left on the custom version.

The zip contains application and network images. Pocket uploads only `omi.signed.bin` (image 0), using MCUmgr over its existing Bluetooth connection. Do not substitute a merged hex file for that binary. This change requires only the application image; the network core remains installed as before.

## What changed

- Connection requests now use 15–30 ms intervals (Bluetooth units 12/24), latency 0, and a 6-second supervision timeout (600 units). The advertised preferred parameters match the explicit request.
- The request is queued immediately when connected. Zephyr's first peripheral request guard is reduced from 5000 ms to 1000 ms. `conn.c:bt_conn_le_param_update` stores the request until that timer expires. The central still chooses the final parameters; they must be checked on a real link.
- Parameter-update callbacks log the result without repeatedly asking the phone to change it again.
- Automatic PHY updates are disabled. Delayed work asks for 1M transmit and receive PHY at 300 ms, replacing the 2M request. There is no RSSI-based 2M mode. The network controller retains its existing capabilities; the application selects 1M.
- Delayed work requests data length and MTU at 1300 ms. The connected callback has no setup sleeps or retry sleeps. MTU failures use the existing delayed recheck (800 ms, at most six attempts). Disconnect cancels the delayed work; workers obtain their own connection reference. The public `bt_conn_foreach` API selects and retains a live connection (`CONFIG_BT_MAX_CONN=1`).
- The Bluetooth revision is `3.0.30-weaklink`; the signed MCUboot image version is `3.0.30+0`.

Pocket's actual Swift `Omi.isNewer` function was extracted and run: custom is newer than `3.0.29`, recovery `3.0.31` is newer than custom, and the original stock revision is older than custom. The build and repository preflight were run. Existing firmware/compiler and advisory preflight warnings remain. No weak-signal radio, audio, reconnect, or physical update test has been performed.

## Build on this Mac

Use the existing NCS v2.9.0 workspace and installed Docker image. Do not run `west update`; this task uses the installed SDK revision and build cache.

```bash
cd ~/Coding/omi-earshot
cp omi/firmware/omi/omi.conf omi/firmware/omi/prj.conf
docker run --rm \
  -v "$PWD/omi/firmware:/omi/firmware" \
  ghcr.io/zephyrproject-rtos/ci:v0.26.13 \
  bash -lc 'pip3 install --quiet ecdsa; cd /omi/firmware/v2.9.0; west build -d build'
```

The existing cache is configured for `omi/nrf5340/cpuapp`, sysbuild, and `/omi/firmware` as `BOARD_ROOT`. For a fresh build, replace `west build -d build` with:

```bash
west build -b omi/nrf5340/cpuapp ../omi --sysbuild -d build --pristine always -- -DBOARD_ROOT=/omi/firmware
```

The output is `omi/firmware/v2.9.0/build/dfu_application.zip`. `prj.conf` is a generated copy of `omi.conf`; do not commit it. RSA-PSS signing is randomized, so a rebuild's complete signed binary and zip hash can differ while the executable payload is identical.

The resident must review the report before bundling into Pocket. Pocket is actually at `~/Coding/pocket` on this Mac. Its `ios/Makefile` target `pendant-firmware` reads the build zip and the Bluetooth version from `omi.conf`; those must describe the same image. That target and any Pocket commits are deliberately left to the resident.

## Finn's update steps

1. Wait for the resident to provide a Pocket build containing `3.0.30-weaklink`.
2. Charge the pendant above 50%. Keep the phone close to the pendant and avoid moving either during the update.
3. Open Pocket, go to **Pendant**, and choose **Update firmware**. Check that the offered version is `3.0.30-weaklink`.
4. Keep Pocket open through upload, confirmation, restart, and reconnection. Allow roughly 2–5 minutes; this is an estimate from the existing OTA guide, not a measured Pocket update time. Do not power off during the restart/write.
5. After reconnection, confirm that the Pendant screen reads `3.0.30-weaklink`. Pocket's `ready` diagnostic event must contain `firmware: 3.0.30-weaklink`. The updater's completion label alone is insufficient: it reflects the intended version before the version is read again.
6. Check that live audio arrives and double taps still work. Inspect the link report for 1M TX/RX and the negotiated interval/timeout. A 15–30 ms interval, latency 0, and 6000 ms timeout are the requested values. Record what iOS actually accepts and how long it takes.
7. Only after the close-range checks, try normal placement and the known weak-link locations. Compare early disconnects, reconnect frequency, and audio gaps with the old firmware. This build is a hypothesis to test, not a measured radio fix.

## Roll back while Bluetooth still works

MCUboot here is overwrite-only (`SB_CONFIG_MCUBOOT_MODE_OVERWRITE_ONLY=y`, effective `CONFIG_BOOT_UPGRADE_ONLY=y`). It replaces the primary application. There is no test-boot revert slot. Pocket uses `.confirmOnly`, so it marks the image confirmed before resetting. A failed application does not automatically restore the previous one.

`CONFIG_MCUBOOT_DOWNGRADE_PREVENTION=y` is effective in the saved bootloader build. MCUboot compares the signed image's major/minor/revision; build-number comparison is disabled. A lower MCUboot version can be uploaded to staging but is rejected at boot. Equal versions are allowed by the comparison (`rc < 0` rejects). The Bluetooth version string is a separate Pocket gate, not MCUboot's security version. Before this change, many stock builds used MCUboot `0.0.0+0` regardless of their Bluetooth revision. After `3.0.30+0`, the original saved `0.0.0+0` image cannot serve as an OTA rollback under this bootloader.

Use the prepared `images/2026-10-25/rollback-3.0.31-stock/dfu_application.zip`. It contains stock source behavior from `1dac191`, with only the Bluetooth string changed to `3.0.31` and the signed header version raised to `3.0.31+0`. Its executable payload was proven byte-for-byte equal to stock after replacing that version text. Its signature was verified with the same key as stock.

The resident must bundle that folder's `omi.signed.bin` into Pocket together with version text `3.0.31`, rebuild/install Pocket, then have Finn repeat the same update steps. Do not run the normal bundling target against the custom zip while merely changing the version text. If using that target, first rebuild stock source with the recovery `prj.conf` and set the version source to `3.0.31`; restore the custom source/config afterward. The saved recovery binary avoids this rebuild.

Confirm `3.0.31` after reconnecting. This is a forward-version reinstall of stock behavior. A later custom update must exceed `3.0.31` in Pocket and use an equal or higher signed MCUboot version; prefer a higher patch number in both. Raising only `+build` will not bypass the bootloader's version check.

To reproduce the recovery image, use a separate checkout of `1dac191934e40378159a1c03bd4ff0b478875a43`, replace DIS `3.0.29` with `3.0.31`, add `CONFIG_MCUBOOT_IMGTOOL_SIGN_VERSION="3.0.31+0"` to the application config, copy it to `prj.conf`, and build with the command above. The exact config is preserved in the recovery folder's `prj.conf`. Keep the same board, signing key, and SDK.

## If it never boots or connects

The effective local bootloader config has `CONFIG_BOOT_USB_DFU_NO=y` and `CONFIG_MCUBOOT_SERIAL` disabled. There is no enabled button-triggered USB/serial recovery in this image. The XIAO reset-button/UF2 instructions are for the nRF52840 DevKit and do not apply to this nRF5340 CV1 pendant.

If the application can still advertise and accept MCUmgr, Bluetooth recovery may remain possible. The Omi app also provides a firmware update flow, but that depends on a working application/Bluetooth service and offers its own chosen release. It cannot rescue a nonbooting application or guarantee an acceptable higher signed version. Use the prepared recovery image through Pocket when the link works.

If the application does not run or provide Bluetooth, use physical SWD recovery: an nRF5340-capable J-Link probe and the special CV1 flashing cable/adapter (or properly identified SWD pads), plus power. Omi's CV1 instructions program the network core first using `merged_CPUNET.hex`, then the application core using `merged.hex`. The original pair is preserved in `stock-3.0.29`; this full physical recovery reinstalls the bootloader as well as the applications. A technician must choose the correct chip/core and check whether access protection requires recovery/erase. That erase can lose device data and settings. No probe connection, erase, or programming command was run here.

Sources: [Omi's CV1 flashing guide](https://docs.omi.me/doc/get_started/Flash_device), [Omi firmware developer kit (J-Link and flash adapter)](https://www.omi.me/products/omi-firmware-developer-kit), and the checked-in SDK's MCUboot `boot/bootutil/src/loader.c` and effective build configs. The hardware recovery path is documented by the vendor; it was not tested on Finn's pendant. The actual pendant bootloader configuration and debug access remain unverified without the hardware.

## Signing evidence

`omi/firmware/omi/sysbuild.conf` sets `SB_CONFIG_BOOT_SIGNATURE_KEY_FILE` to `${APP_DIR}/../bootloader/mcuboot/root-rsa-2048.pem`. The effective application config resolves `CONFIG_MCUBOOT_SIGNATURE_KEY_FILE` to `/omi/firmware/bootloader/mcuboot/root-rsa-2048.pem`. The effective MCUboot config uses the same path as `CONFIG_BOOT_SIGNATURE_KEY_FILE` and RSA-2048 validation. No key was changed.

All three signed application images pass the installed MCUboot `imgtool verify`. The public key derived from that file equals the generated MCUboot public-key array and occurs in the preserved stock merged hex's bootloader region. The rebuilt bootloader's bytes also match that region. This proves compatibility with the preserved local bootloader image. It does not independently prove what bootloader is physically installed.
