import path from "node:path";
import { promises as fs } from "node:fs";

const repoRoot = path.resolve(process.cwd(), "..");
const webRoot = process.cwd();
const releaseRoot = path.join(repoRoot, "release-data");
const verifiedAnswersPath = path.join(repoRoot, "src", "kangaroo_pdf", "verified_answer_keys.json");
const outputDataRoot = path.join(webRoot, "data");
const outputExamRoot = path.join(outputDataRoot, "exams");
const outputPublicRoot = path.join(webRoot, "public", "exams");

const FAMILY_META = {
  canada_gr0102e_18: {
    startingPoints: 18,
    durationMinutes: 45,
    penaltyMode: "minus_one",
    familyLabel: "Canada Grade 1-2",
    originLabel: "Canada",
  },
  felix_austria_15: {
    startingPoints: 15,
    durationMinutes: 60,
    penaltyMode: "minus_quarter",
    familyLabel: "Felix Austria",
    originLabel: "Austria",
  },
  felix_brazil_24: {
    startingPoints: 24,
    durationMinutes: 100,
    penaltyMode: "minus_quarter",
    familyLabel: "Felix Brazil",
    originLabel: "Brazil",
  },
};

async function main() {
  const manifest = await readJson(path.join(releaseRoot, "manifest.json"));
  const verifiedAnswers = await readJson(verifiedAnswersPath);

  await fs.rm(outputDataRoot, { recursive: true, force: true });
  await fs.rm(outputPublicRoot, { recursive: true, force: true });
  await fs.mkdir(outputExamRoot, { recursive: true });
  await fs.mkdir(outputPublicRoot, { recursive: true });

  const examSummaries = [];
  const questionIndex = [];

  for (const manifestEntry of manifest.exams) {
    const examFile = path.join(releaseRoot, manifestEntry.path);
    const examDirectory = path.dirname(examFile);
    const exam = await readJson(examFile);
    const verified = verifiedAnswers[exam.exam_id];

    if (!verified) {
      throw new Error(`Missing verified answer key for ${exam.exam_id}`);
    }

    if (JSON.stringify(exam.answer_key) !== JSON.stringify(verified)) {
      throw new Error(`Answer key mismatch for ${exam.exam_id}`);
    }

    const familyMeta = FAMILY_META[exam.family];
    const durationMinutes = exam.duration_minutes ?? familyMeta.durationMinutes;
    const maxQuestionPoints = exam.scoring_rules.reduce(
      (total, rule) => total + (rule.to - rule.from + 1) * rule.points,
      0,
    );
    const assetById = Object.fromEntries(exam.assets.map((asset) => [asset.id, asset]));
    const publicExamDir = path.join(outputPublicRoot, exam.exam_id);
    const publicAssetDir = path.join(publicExamDir, "assets");

    await fs.mkdir(publicAssetDir, { recursive: true });

    for (const asset of exam.assets) {
      const sourcePath = path.join(examDirectory, asset.path);
      const targetPath = path.join(publicExamDir, asset.path);
      await fs.mkdir(path.dirname(targetPath), { recursive: true });
      await fs.copyFile(sourcePath, targetPath);
    }

    const normalizedQuestions = exam.questions.map((question) => ({
      id: question.id,
      number: question.number,
      part: question.part,
      points: question.points,
      stemText: cleanText(question.stem_text),
      rawStemText: question.stem_text,
      stemAssets: question.shared_asset_refs.map((ref) => toAsset(assetById[ref], exam.exam_id)),
      choices: question.choices.map((choice) => ({
        label: choice.label,
        text: cleanText(choice.text),
        rawText: choice.text,
        assets: choice.asset_refs.map((ref) => toAsset(assetById[ref], exam.exam_id)),
      })),
      correctLabel: verified[String(question.number)],
    }));

    const summary = {
      examId: exam.exam_id,
      title: buildExamTitle(manifestEntry),
      subtitle: `${familyMeta.originLabel} · ${manifestEntry.year} · ${exam.question_count} questions`,
      family: exam.family,
      familyLabel: familyMeta.familyLabel,
      originLabel: familyMeta.originLabel,
      year: manifestEntry.year,
      level: exam.level,
      language: exam.language,
      questionCount: exam.question_count,
      durationMinutes,
      maxScore: familyMeta.startingPoints + maxQuestionPoints,
      startingPoints: familyMeta.startingPoints,
      penaltyMode: familyMeta.penaltyMode,
      rulesSummary: exam.scoring_rules
        .map((rule) => `Q${rule.from}-${rule.to}: ${rule.points} pts`)
        .join(" · "),
      penaltySummary:
        familyMeta.penaltyMode === "minus_one"
          ? "Incorrect answers deduct 1 point. Blanks are worth 0."
          : "Incorrect answers deduct 25% of that question's value. Blanks are worth 0.",
      officialDuration: exam.duration_minutes !== null,
      availableQuestionNumbers: normalizedQuestions.map((question) => question.number),
    };

    examSummaries.push(summary);

    for (const question of normalizedQuestions) {
      questionIndex.push({
        key: `${summary.examId}:${question.number}`,
        examId: summary.examId,
        examTitle: summary.title,
        family: summary.family,
        familyLabel: summary.familyLabel,
        year: summary.year,
        questionNumber: question.number,
        part: question.part,
        points: question.points,
      });
    }

    await writeJson(path.join(outputExamRoot, `${exam.exam_id}.json`), {
      ...summary,
      instructions: exam.instructions.map(cleanInstruction).filter(Boolean),
      rawInstructions: exam.instructions,
      questions: normalizedQuestions,
    });
  }

  await writeJson(path.join(outputDataRoot, "catalog.json"), {
    generatedAt: manifest.generated_at,
    examCount: examSummaries.length,
    questionCount: questionIndex.length,
    exams: examSummaries.sort((left, right) => right.year - left.year || left.title.localeCompare(right.title)),
    questionIndex: questionIndex.sort((left, right) =>
      left.examId.localeCompare(right.examId) || left.questionNumber - right.questionNumber,
    ),
  });
}

function buildExamTitle(entry) {
  if (entry.exam_id.startsWith("canada")) {
    return `Canada Grade 1-2 ${entry.year}`;
  }

  if (entry.exam_id.startsWith("felix-austria")) {
    return `Felix Austria ${entry.year}`;
  }

  if (entry.exam_id.startsWith("felix-brazil")) {
    return `Felix Brazil ${entry.year}`;
  }

  return entry.exam_id;
}

function cleanInstruction(value) {
  const cleaned = cleanText(value);
  if (!cleaned) {
    return "";
  }

  if (/^(name|school|class):?$/i.test(cleaned)) {
    return "";
  }

  return cleaned;
}

function cleanText(value) {
  if (!value) {
    return "";
  }

  let cleaned = value.trim();
  cleaned = cleaned.replace(
    /^Thi t i l b d d l ith th i i f th C di M th K C t t C ti P \d+\s*/i,
    "",
  );
  cleaned = cleaned.replace(
    /This material may be reproduced only with the permission of the Canadian Math Kangaroo Contest Corporation\.?/gi,
    "",
  );
  cleaned = cleaned.replace(/\b([0-9]+)i\b/g, "$1");
  cleaned = cleaned.replace(/\bi\b/g, "");
  cleaned = cleaned.replace(/\s+/g, " ").trim();
  cleaned = cleaned.replace(/^E\s+$/, "E");
  return cleaned;
}

function toAsset(asset, examId) {
  if (!asset) {
    throw new Error(`Missing asset metadata while generating ${examId}`);
  }

  return {
    id: asset.id,
    url: `/${["exams", examId, asset.path].join("/")}`,
    width: asset.width,
    height: asset.height,
    kind: asset.kind,
    role: asset.role,
    mediaType: asset.media_type,
  };
}

async function readJson(filePath) {
  return JSON.parse(await fs.readFile(filePath, "utf8"));
}

async function writeJson(filePath, value) {
  await fs.mkdir(path.dirname(filePath), { recursive: true });
  await fs.writeFile(filePath, `${JSON.stringify(value, null, 2)}\n`, "utf8");
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
