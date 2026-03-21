import catalog from "../data/catalog.json";
import canada2023 from "../data/exams/canada-gr0102e-2023.json";

describe("generated catalog data", () => {
  it("includes the expected paper and question totals", () => {
    expect(catalog.examCount).toBe(16);
    expect(catalog.questionCount).toBe(270);
    expect(catalog.exams).toHaveLength(16);
    expect(catalog.questionIndex).toHaveLength(270);
  });

  it("keeps asset URLs deployable from the web app", () => {
    const firstQuestion = canada2023.questions[0];
    expect(firstQuestion.stemAssets[0]?.url).toBe("/exams/canada-gr0102e-2023/assets/q01_stem_01.png");
  });

  it("cleans the known OCR noise patterns without dropping the actual answer text", () => {
    const questionOne = canada2023.questions.find((question) => question.number === 1);
    const questionTwo = canada2023.questions.find((question) => question.number === 2);
    const questionFour = canada2023.questions.find((question) => question.number === 4);

    expect(questionOne?.choices.find((choice) => choice.label === "E")?.text).toBe("9");
    expect(questionTwo?.choices.find((choice) => choice.label === "E")?.text).toBe("");
    expect(questionFour?.choices.find((choice) => choice.label === "E")?.text).toBe("5 7");
  });
});
