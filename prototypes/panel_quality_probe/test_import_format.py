import tempfile
from pathlib import Path
import unittest

from PIL import Image, features

from import_format import prepare_publication_image, digest


class PublicationFormatTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.pages = self.root / 'pages'

    def prepare(self, source, name='0001'):
        return prepare_publication_image(source, self.pages / name,
            self.pages / 'source-auxiliary' / 'original-images', source_locator=source.name)

    def test_upright_compatible_bytes_are_unchanged(self):
        for extension in ('jpg', 'jpeg', 'png'):
            with self.subTest(extension=extension):
                source = self.root / ('source.' + extension)
                Image.new('RGB', (12, 20), '#4488aa').save(source)
                result = self.prepare(source, extension)
                self.assertEqual(result['sha256'], digest(source))
                self.assertEqual(result['publication_transforms'], [])
                self.assertIsNone(result['preserved_original'])

    def test_other_stills_are_png_with_original_bytes_retained(self):
        formats = ['bmp', 'gif'] + (['webp'] if features.check('webp') else [])
        for extension in formats:
            with self.subTest(extension=extension):
                source = self.root / ('source.' + extension)
                Image.new('RGB', (12, 20), '#4488aa').save(source)
                original = source.read_bytes()
                result = self.prepare(source, extension)
                self.assertTrue(result['image'].endswith('.png'))
                with Image.open(source) as old, Image.open(self.pages / result['image']) as new:
                    self.assertEqual(old.convert('RGBA').tobytes(), new.convert('RGBA').tobytes())
                self.assertEqual((self.pages / result['preserved_original']).read_bytes(), original)
                self.assertEqual(source.read_bytes(), original)
                self.assertEqual(result['original_sha256'], digest(source))

    def test_exif_rotation_is_applied_once_and_original_retained(self):
        source = self.root / 'rotated.jpg'
        im = Image.new('RGB', (12, 20), 'red')
        im.paste('blue', (0, 0, 12, 10))
        exif = Image.Exif(); exif[274] = 6
        im.save(source, exif=exif)
        result = self.prepare(source)
        self.assertEqual([result['width'], result['height']], [20, 12])
        self.assertEqual(result['publication_transforms'], ['exif-transpose', 'encode-png'])
        with Image.open(self.pages / result['image']) as published:
            self.assertEqual(published.getexif().get(274, 1), 1)
            self.assertGreater(published.getpixel((2, 5))[0], published.getpixel((2, 5))[2])
            self.assertGreater(published.getpixel((17, 5))[2], published.getpixel((17, 5))[0])

    def test_animation_is_rejected_before_any_output(self):
        source = self.root / 'moving.gif'
        Image.new('RGB', (12, 20), 'red').save(source, save_all=True,
            append_images=[Image.new('RGB', (12, 20), 'blue')], duration=100, loop=0)
        before = source.read_bytes()
        with self.assertRaisesRegex(ValueError, 'animated or multipage'):
            self.prepare(source)
        self.assertFalse(self.pages.exists())
        self.assertEqual(source.read_bytes(), before)

    def test_transparent_still_preserves_alpha(self):
        source = self.root / 'transparent.gif'
        image = Image.new('P', (12, 20)); image.putpalette([255, 0, 0] + [0] * 765)
        image.info['transparency'] = 0; image.save(source)
        result = self.prepare(source)
        with Image.open(self.pages / result['image']) as published:
            self.assertEqual(published.mode, 'RGBA')
            self.assertEqual(published.getpixel((0, 0))[3], 0)

    def test_collision_and_symlink_cannot_overwrite_data(self):
        source = self.root / 'still.bmp'
        Image.new('RGB', (12, 20), 'red').save(source)
        result = self.prepare(source)
        before = (self.pages / result['image']).read_bytes()
        with self.assertRaises(FileExistsError): self.prepare(source)
        self.assertEqual((self.pages / result['image']).read_bytes(), before)
        link = self.root / 'link.bmp'; link.symlink_to(source)
        with self.assertRaisesRegex(ValueError, 'nonsymlink'): self.prepare(link, '0002')


if __name__ == '__main__': unittest.main()
