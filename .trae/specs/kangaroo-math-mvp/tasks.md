# Tasks

- [x] Task 1: Project Initialization & Setup
    - [x] SubTask 1.1: Initialize React project with Vite and TypeScript.
    - [x] SubTask 1.2: Install and configure Tailwind CSS with custom Duolingo-style colors and border radius.
    - [x] SubTask 1.3: Set up project folder structure (components, hooks, context, types, utils).
    - [x] SubTask 1.4: Configure routing (React Router) for Home, Exam, and Report pages.

- [x] Task 2: Data Management Layer
    - [x] SubTask 2.1: Define TypeScript interfaces for Exam and Question data based on JSON schema.
    - [x] SubTask 2.2: Implement a service to load and parse `processed/exams/*.json`.
    - [x] SubTask 2.3: Create a React Context/Store (`ExamContext`) to manage exam state (current question index, answers map, time elapsed, exam status).
    - [x] SubTask 2.4: Implement `useLocalStorage` hook to persist and rehydrate exam state.

- [x] Task 3: Core UI Components Implementation
    - [x] SubTask 3.1: Create `Button` component (variants: primary, danger, outline; large sizes).
    - [x] SubTask 3.2: Create `ProgressBar` component (visualizing answered/total).
    - [x] SubTask 3.3: Create `QuestionNavigation` component (grid of numbers with status colors).
    - [x] SubTask 3.4: Create `QuestionCard` component to display Stem (text + graphics) and Options.
    - [x] SubTask 3.5: Implement layout container with sidebar/drawer for navigation and main content area.

- [x] Task 4: Exam Logic & Interaction
    - [x] SubTask 4.1: Implement "Next" and "Previous" navigation logic with boundary checks.
    - [x] SubTask 4.2: Implement "Jump to Question" logic from the navigation grid.
    - [x] SubTask 4.3: Implement Answer Selection logic (update state, persist).
    - [x] SubTask 4.4: Implement "Skip" functionality.
    - [x] SubTask 4.5: Implement Timer hook and display.
    - [x] SubTask 4.6: Implement Preloading logic (fetch/cache adjacent question assets if dynamic, or just ensure state readiness).

- [x] Task 5: Exam Submission & Reporting
    - [x] SubTask 5.1: Create "End Exam" button and Confirmation Modal.
    - [x] SubTask 5.2: Implement scoring logic (calculate score based on `answer` field and points).
    - [x] SubTask 5.3: Create `ReportPage` to display results (Score, Accuracy, list of mistakes).
    - [x] SubTask 5.4: Add "Review" mode to let users see their answers vs correct answers (optional MVP feature, but good for report).

- [x] Task 6: Visual Polish & Final Integration
    - [x] SubTask 6.1: Apply final Duolingo-style styling (shadows, transitions, hover states).
    - [x] SubTask 6.2: Add placeholder mascot/cartoon elements.
    - [x] SubTask 6.3: Conduct responsiveness check (mobile/desktop).
    - [x] SubTask 6.4: Verify performance (response time, 100-question stress test simulation).

# Task Dependencies
- Task 3 depends on Task 1.
- Task 4 depends on Task 2 and Task 3.
- Task 5 depends on Task 4.
- Task 6 depends on all previous tasks.
