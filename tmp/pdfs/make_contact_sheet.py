from pathlib import Path

from PIL import Image, ImageOps, ImageDraw


def make_sheet(pages: list[int], output: str) -> None:
    images = []
    for page in pages:
        image = Image.open(Path(__file__).parent / f"designguideline-{page}.png").convert("RGB")
        image = ImageOps.contain(image, (900, 1275))
        canvas = Image.new("RGB", (920, 1325), "white")
        canvas.paste(image, ((920 - image.width) // 2, 40))
        ImageDraw.Draw(canvas).text((15, 12), f"PDF page {page}", fill="black")
        images.append(canvas)

    sheet = Image.new("RGB", (1840, 2650), "white")
    for index, image in enumerate(images):
        sheet.paste(image, ((index % 2) * 920, (index // 2) * 1325))
    sheet.save(Path(__file__).parent / output, quality=92)


make_sheet([37, 38, 39, 40], "guideline-power.jpg")
make_sheet([41, 42, 43, 44], "guideline-analog-digital.jpg")
make_sheet([45, 46, 47, 50], "guideline-thermal-checklist.jpg")
