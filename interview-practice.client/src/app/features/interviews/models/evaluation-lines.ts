/** A bullet or number the model put in front of a line ("- ", "* ", "1. ", "2) "). */
const LIST_MARKER = /^(?:[-*•]|\d+[.)])\s+/;

/** The items of an Evaluation text field that holds one item per line. */
export function evaluationLines(text: string): string[] {
  return text
    .split('\n')
    .map((line) => line.trim().replace(LIST_MARKER, ''))
    .filter((line) => line.length > 0);
}
