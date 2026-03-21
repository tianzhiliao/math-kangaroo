export function formatDuration(minutes: number) {
  const hours = Math.floor(minutes / 60);
  const remainder = minutes % 60;

  if (hours === 0) {
    return `${minutes} min`;
  }

  if (remainder === 0) {
    return `${hours}h`;
  }

  return `${hours}h ${remainder}m`;
}

export function buildQuestionKey(examId: string, questionNumber: number) {
  return `${examId}:${questionNumber}`;
}
