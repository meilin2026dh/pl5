export type SequenceConfig = { context: 4 | 8 | 12; epochs: number };
export const defaultSequence: SequenceConfig = { context: 8, epochs: 20 };
export function validateSequence(c: SequenceConfig) {
  if (
    !c ||
    ![4, 8, 12].includes(c.context) ||
    !Number.isInteger(c.epochs) ||
    c.epochs < 1 ||
    c.epochs > 20
  )
    throw Error("时序上下文须4/8/12，训练轮数1—20");
}
