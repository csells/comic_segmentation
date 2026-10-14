"""Create an RTL regression fixture with equal-camera, different-mask frames.

Run only in the disposable browser VM. This synthetic book is test data, not a
segmentation result. Both frames have the same center and height; viewport height
limits their scale, so only the child dimming mask animates between them.
"""
import hashlib
import io
import json
from pathlib import Path
import sys
import zipfile

from PIL import Image, ImageDraw


target = Path(sys.argv[1])
image = Image.new('RGB', (600, 800), '#c0d7e8')
draw = ImageDraw.Draw(image)
draw.rectangle((200, 100, 400, 700), fill='#316aa3')
draw.rectangle((250, 100, 350, 700), fill='#f19f42')
for y in range(150, 700, 100): draw.line((200, y, 400, y), fill='white', width=4)
buffer = io.BytesIO(); image.save(buffer, format='PNG')
metadata = b'''<?xml version="1.0" encoding="UTF-8"?>
<ACBF xmlns="http://www.acbf.info/xml/acbf/1.1"><meta-data><book-info>
<book-title>Traversal regression: equal camera, different mask</book-title>
<coverpage><image href="page.png"/>
<frame points="200,100 400,100 400,700 200,700"/>
<frame points="250,100 350,100 350,700 250,700"/>
</coverpage></book-info></meta-data></ACBF>'''
profile = {'format':'comic-panel-reader-profile','version':1,'reading_direction':'rtl',
           'metadata_sha256':hashlib.sha256(metadata).hexdigest()}
with zipfile.ZipFile(target, 'x', compression=zipfile.ZIP_DEFLATED) as archive:
    archive.writestr('page.png', buffer.getvalue())
    archive.writestr('metadata.acbf', metadata)
    archive.writestr('panel-reader.json', json.dumps(profile))
print(target)
