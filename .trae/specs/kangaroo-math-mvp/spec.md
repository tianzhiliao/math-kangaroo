# Kangaroo Math MVP Web App Spec

## Why
To provide an engaging, focused, and user-friendly platform for students to practice Kangaroo Math exams, breaking away from traditional paper-based or linear digital formats. The goal is to create an MVP that validates the core exam experience with a modern, gamified UI.

## What Changes
- **New Application**: A React-based Single Page Application (SPA) using Vite.
- **Data Integration**: A loader mechanism to read and parse exam data from `processed/exams/*.json`.
- **UI/UX Overhaul**: A Duolingo-inspired interface with high saturation colors, rounded corners, and playful interactions.

## Impact
- **Affected Specs**: None (New Project).
- **Affected Code**: New directory `kangaroo-math-mvp` (or root if starting fresh).
- **Data Dependency**: Depends on the schema of JSON files in `processed/exams/`.

## ADDED Requirements

### Requirement: Exam Core
The system SHALL provide a mock exam environment.
- **Data Source**: Load exams from `processed/exams/Exam_2020.json`, `Exam_2021.json`, etc.
- **Mode**: Single Question Mode (one question per screen).
- **Navigation**: Free navigation via a question number grid/panel.
- **State Management**:
    - **Persistence**: Save progress (answers, time, current question) to LocalStorage.
    - **Real-time**: Update status immediately upon interaction.
    - **Preloading**: Preload ±5 questions around the current one for instant navigation.

### Requirement: Interactive Features
- **Answering**:
    - Select an option (A-E).
    - Change selected option.
    - **Skip**: Explicit "Skip" button to mark for later.
- **Visual Feedback**:
    - **Green**: Answered.
    - **Gray**: Unanswered/Skipped.
    - **Progress Bar**: Visual indicator of overall completion.
- **Timer**: A non-intrusive timer counting up or down (configurable, default count up for MVP).
- **Submission**:
    - "End Exam" button available at any time.
    - Secondary confirmation dialog before finalizing.
- **Report**:
    - Summary of Score, Accuracy.
    - List of incorrect questions with correct answers.

### Requirement: Visual Design (Duolingo Style)
- **Colors**:
    - Primary: #58CC02 (Green)
    - Error/Danger: #FF4B4B (Red)
    - Warning/Highlight: #FFC800 (Yellow)
    - Neutral: White, Light Grays.
- **Typography**: Large font sizes (>=20px for body text).
- **Components**:
    - **Cards**: Rounded corners (border-radius >= 12px).
    - **Buttons**: Super-sized (height >= 48px), pill-shaped or rounded.
    - **Mascot**: Include placeholder for a mascot/cartoon element (e.g., a Kangaroo).

### Requirement: Technical Performance
- **Responsiveness**: Perfect display at 1080p, functional on mobile/tablet.
- **Browser Support**: Chrome, Safari, Edge (latest versions).
- **Performance**: <200ms interaction response time.
- **Stress Test**: Handle 100 continuous question interactions without lag.
