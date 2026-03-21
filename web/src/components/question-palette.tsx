"use client";

interface QuestionPaletteProps {
  numbers: number[];
  currentQuestion: number;
  answered?: number[];
  marked?: number[];
  correct?: number[];
  incorrect?: number[];
  onJump: (questionNumber: number) => void;
  title?: string;
  note?: string;
}

export function QuestionPalette({
  numbers,
  currentQuestion,
  answered = [],
  marked = [],
  correct = [],
  incorrect = [],
  onJump,
  title = "Question map",
  note = "Jump anywhere at any time.",
}: QuestionPaletteProps) {
  const answeredSet = new Set(answered);
  const markedSet = new Set(marked);
  const correctSet = new Set(correct);
  const incorrectSet = new Set(incorrect);

  return (
    <aside className="panel drawer">
      <div className="panel-inner">
        <div className="field-stack">
          <div>
            <div className="eyebrow">Navigator</div>
            <h3 className="section-title" style={{ fontSize: "1.6rem", marginBottom: 6 }}>
              {title}
            </h3>
            <p className="lede">{note}</p>
          </div>
          <div className="palette-grid">
            {numbers.map((number) => (
              <button
                type="button"
                className="palette-button"
                key={number}
                data-current={number === currentQuestion}
                data-answered={answeredSet.has(number)}
                data-marked={markedSet.has(number)}
                data-correct={correctSet.has(number)}
                data-incorrect={incorrectSet.has(number)}
                onClick={() => onJump(number)}
              >
                {number}
              </button>
            ))}
          </div>
        </div>
      </div>
    </aside>
  );
}
