/* Presentation steps are separate from the book's original panel metadata. */
export function guidedSteps(rects, width, height) {
  const overview = {x: 0, y: 0, width, height, overview: true};
  const fullPage = rects.length === 1 && rects[0].x <= 1 && rects[0].y <= 1 &&
    Math.abs(rects[0].x + rects[0].width - width) <= 1 &&
    Math.abs(rects[0].y + rects[0].height - height) <= 1;
  return fullPage || !rects.length ? [overview] : [overview, ...rects];
}
