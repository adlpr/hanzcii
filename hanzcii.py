#!/usr/bin/python3
# -*- coding: UTF-8 -*-

import argparse, json

import numpy as np
from PIL import Image, ImageFont, ImageDraw, ImageEnhance
from tqdm import tqdm
from loguru import logger


def main(args):
    logger.info(f"initializing hanzi comparator")
    hc = HanziComparator()

    # open image and convert to 8-bit monochrome
    logger.info(f"reading image file {args.IMG}")
    img = Image.open(args.IMG)
    if img.mode in ("RGBA","RGBa"):
        # set any transparent parts to white by pasting onto new image w/o alpha
        img_rgb = Image.new("RGB", img.size, "WHITE")
        img_rgb.paste(img, (0, 0), img)
        img = img_rgb

    # optional image enhancements
    if args.contrast != 1.0:
        logger.info(f"adjusting contrast, factor: {args.contrast}")
        enh = ImageEnhance.Contrast(img)
        img = enh.enhance(args.contrast)
        del enh
    if args.sharpness != 1.0:
        logger.info(f"adjusting sharpness, factor: {args.sharpness}")
        enh = ImageEnhance.Sharpness(img)
        img = enh.enhance(args.sharpness)
        del enh
    if args.brightness != 1.0:
        logger.info(f"adjusting brightness, factor: {args.brightness}")
        enh = ImageEnhance.Brightness(img)
        img = enh.enhance(args.brightness)
        del enh

    # convert to 8-bit monochrome (uint8) np ndarray
    logger.info("converting image to uint8 ndarray")
    img = np.array(img.convert("L"))

    # slice and compare each 8x8 chunk
    logger.info("slicing 8x8")
    sliced = slice_to_8x8(img)
    total_rows = len(sliced)
    logger.info("converting slices to characters")
    result = ""
    for i, row in enumerate(sliced):
        logger.info(f"row {i+1} of {total_rows}...")
        for slice in tqdm(row):
            result += hc.get_best(slice)
        result += "\n"

    logger.success("done!")
    print("\n"+result+"\n")

    # output result
    outfn = args.output or (args.IMG + ".txt")
    logger.success(f"outputting to file {outfn}")
    with open(outfn, "w") as outf:
        outf.write(result)


def slice_to_8x8(arr: np.ndarray) -> list:
    # first pad with white to multiple of 8
    h, w = arr.shape
    pad_h, pad_w = (8-h)%8, (8-w)%8
    arr = np.pad(arr, ((pad_h//2,round(pad_h/2)),((pad_w//2,round(pad_w/2)))), constant_values=0xFF)
    # then slice into 2d list of 8x8 ndarrays
    h, w = arr.shape    # (should now both be mults of 8)
    result = []
    for ih in range(0,h,8):
        result.append([])
        for iw in range(0,w,8):
            result[-1].append(arr[ih:ih+8, iw:iw+8])
    return result


class HanziComparator:
    def __init__(self, arrays_json: str = "hanzi_arrays.json",
                       font_file: str = "JF-Dot-Shinonome16.ttf") -> None:
        self.arrays_json = arrays_json
        self.font_file = font_file
        try:
            with open(arrays_json, "r") as inf:
                self.hanzi_arrays = json.load(inf)
        except:
            logger.warning("references file not found, regenerating")
            self.hanzi_arrays = self.__generate_arrays()

    def __generate_arrays(self) -> dict:
        logger.info(f"generating references from font {self.font_file}")
        hanzi_arrays = {}
        # blank array = whitespace
        blank_8x8 = np.zeros((8,8)).astype("uint8")
        blank_8x8.fill(0xFF)
        hanzi_arrays["\u3000"] = blank_8x8
        font = ImageFont.truetype(self.font_file, 16)
        for char in tqdm(map(chr, range(0x4E00, 0xA000))):
            # draw 16-pt character on a 16x16 surface
            img = Image.new("L", (16,16), 0xFF)
            drw = ImageDraw.Draw(img)
            drw = drw.text((0,0), char, 0x00, font=font)
            # is this character not in the font?
            if np.array(img).tolist() == self.REPLACEMENT_CHAR_16X16:
                continue
            # downsample to 8x8 and save in dict
            img = img.resize((8,8), Image.LANCZOS)
            hanzi_arrays[char] = np.array(img)
        logger.info(f"saving to {self.arrays_json}...")
        try:
            with open(self.arrays_json, "w") as outf:
                json.dump({k:v.tolist() for k,v in hanzi_arrays.items()}, outf)
            logger.success("saved references")
        except:
            logger.error("failed saving to disk")
        return hanzi_arrays

    def get_best(self, inp: np.ndarray) -> str:
        """
        get character mapped to array with highest similarity to input
        """
        return max([(self.similarity(inp, arr), hanzi) for hanzi, arr in self.hanzi_arrays.items()])[1]

    @staticmethod
    def similarity(this: np.ndarray, that: np.ndarray) -> int:
        """
        super naive comparison of 2d arrays: sum |diffs|
        """
        return -sum(sum(abs(this-that)))

    REPLACEMENT_CHAR_16X16 = \
    [[255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,169,135,135,169,255,255,255,255,255,255],
     [255,255,255,255,255,255, 71,  0,  0, 71,255,255,255,255,255,255],
     [255,255,255,255,255,255, 71,  0,  0, 71,255,255,255,255,255,255],
     [255,255,255,255,255,255, 77,  7,  7, 77,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255],
     [255,255,255,255,255,255,255,255,255,255,255,255,255,255,255,255]]



if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("IMG", help="input image filename")
    parser.add_argument("-o", "--output", type=str, default="", help="output text filename; default is input image filename + .txt)")
    parser.add_argument("-c", "--contrast", type=float, default=1.0, help="adjust input contrast with PIL.ImageEnhance.Contrast; default 1.0")
    parser.add_argument("-s", "--sharpness", type=float, default=1.0, help="sharpen/blur input with PIL.ImageEnhance.Sharpness; default 1.0")
    parser.add_argument("-b", "--brightness", type=float, default=1.0, help="brighten input with PIL.ImageEnhance.Brightness; default 1.0")
    main(parser.parse_args())
