/** Make a photo small enough to upload: at most `maxSide` pixels on its longest side, saved as a JPEG.
 *  Phone photos are often 3–5 MB; this brings them to a few hundred KB, still sharp enough to read.
 *  Redrawing the picture also drops the hidden extras a camera adds, such as where the photo was taken. */
export async function shrinkImage(file: Blob, maxSide = 1600, quality = 0.85): Promise<Blob> {
  let bitmap: ImageBitmap;
  try {
    bitmap = await createImageBitmap(file, { imageOrientation: "from-image" }); // turned the way the camera held it
  } catch {
    throw new Error("This browser can't open that file. Choose a JPG, PNG or WebP picture");
  }
  const scale = Math.min(1, maxSide / Math.max(bitmap.width, bitmap.height));
  const canvas = document.createElement("canvas");
  canvas.width = Math.round(bitmap.width * scale);
  canvas.height = Math.round(bitmap.height * scale);
  const ctx = canvas.getContext("2d");
  if (!ctx) throw new Error("This browser can't prepare the picture");
  ctx.fillStyle = "#fff"; // a see-through PNG would otherwise turn black as a JPEG
  ctx.fillRect(0, 0, canvas.width, canvas.height);
  ctx.drawImage(bitmap, 0, 0, canvas.width, canvas.height);
  bitmap.close();
  const blob = await new Promise<Blob | null>((done) => canvas.toBlob(done, "image/jpeg", quality));
  if (!blob) throw new Error("This browser can't prepare the picture");
  return blob;
}
