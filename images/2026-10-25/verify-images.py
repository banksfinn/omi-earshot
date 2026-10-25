from pathlib import Path
import zipfile, struct, hashlib, subprocess, re
from cryptography.hazmat.primitives import serialization
from intelhex import IntelHex
root=Path('/repo'); images=root/'images/2026-10-25'
key=root/'omi/firmware/bootloader/mcuboot/root-rsa-2048.pem'
public=serialization.load_pem_private_key(key.read_bytes(),password=None).public_key().public_bytes(serialization.Encoding.DER, serialization.PublicFormat.PKCS1)
autogen=(images/'weaklink-3.0.30/mcuboot-autogen-pubkey.c').read_text().split('};')[0]
compiled=bytes(int(v,16) for v in re.findall(r'0x([0-9a-fA-F]{2})',autogen))
assert compiled==public
stockhex=IntelHex(str(images/'stock-3.0.29/merged.hex'))
assert public in bytes(stockhex.tobinarray(start=0,end=0xffff))
print('Signing public key matches generated bootloader key AND preserved stock bootloader bytes')
print('Public key SHA256:',hashlib.sha256(public).hexdigest())
payloads={}
for folder in ['stock-3.0.29','weaklink-3.0.30','rollback-3.0.31-stock']:
 d=images/folder; data=zipfile.ZipFile(d/'dfu_application.zip').read('omi.signed.bin'); (d/'omi.signed.bin').write_bytes(data)
 h=struct.unpack_from('<H',data,8)[0]; n=struct.unpack_from('<I',data,12)[0]; ver=struct.unpack_from('<BBHI',data,20); payloads[folder]=data[h:h+n]
 print(folder,'MCUboot version',ver,'signed SHA256',hashlib.sha256(data).hexdigest(),'payload SHA256',hashlib.sha256(data[h:h+n]).hexdigest())
 subprocess.run(['python3',str(root/'omi/firmware/v2.9.0/bootloader/mcuboot/scripts/imgtool.py'),'verify','-k',str(key),str(d/'omi.signed.bin')],check=True)
stock=payloads['stock-3.0.29']; rollback=payloads['rollback-3.0.31-stock']
assert stock.replace(b'3.0.29\0',b'3.0.31\0')==rollback, 'rollback differs beyond DIS revision'
print('PASS: rollback executable payload is byte-for-byte stock after replacing only DIS 3.0.29 with 3.0.31')
for d in images.iterdir():
 if d.is_dir(): (d/'SHA256SUMS').write_text(''.join(hashlib.sha256(f.read_bytes()).hexdigest()+'  '+f.name+'\n' for f in sorted(d.iterdir()) if f.is_file() and f.name!='SHA256SUMS'))
