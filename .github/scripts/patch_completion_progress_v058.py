from pathlib import Path

p = Path('he/workspace/lesson-completion.js')
text = p.read_text(encoding='utf-8')

old = '''  const totalLessons =
    Math.max(
      lessons.length,
      currentOrder
    );

  const completedCount =
    Math.min(
      currentOrder,
      totalLessons
    );

  const unitProgress =
    totalLessons
      ? Math.round(
          completedCount
          /
          totalLessons
          * 100
        )
      : 100;
'''
new = '''  const totalLessons =
    Math.max(
      lessons.length,
      currentOrder
    );

  const savedProgressRows =
    Array.isArray(window.LESSON_SIDEBAR_PROGRESS_ROWS)
      ? window.LESSON_SIDEBAR_PROGRESS_ROWS
      : [];

  const progressByLessonId =
    new Map(
      savedProgressRows.map(
        row => [Number(row?.unit_lesson_id || 0), row]
      )
    );

  const completedCount =
    lessons.filter(
      lesson =>
        String(
          progressByLessonId.get(Number(lesson?.id || 0))?.status
          || "not_started"
        ) === "completed"
    ).length;

  const unitProgress =
    totalLessons
      ? Math.round(
          completedCount
          /
          totalLessons
          * 100
        )
      : 100;
'''
if old not in text:
    raise SystemExit('completion count block not found')
text = text.replace(old, new, 1)

old = '''              const isCompleted =
                order <= currentOrder;

              const isNext =
                order === currentOrder + 1;

              const stateClass =
                isCompleted
                  ? "completed"
                  : isNext
                    ? "next"
                    : "locked";

              const status =
                isCompleted
                  ? (
                      order === currentOrder
                        ? `הושלם • ${score}%`
                        : "הושלם ✓"
                    )
                  : isNext
                    ? "השיעור הבא"
                    : "טרם נפתח 🔒";

              const button =
                isNext
'''
new = '''              const savedProgress =
                progressByLessonId.get(
                  Number(lesson?.id || 0)
                ) || null;

              const savedStatus =
                String(
                  savedProgress?.status
                  || "not_started"
                );

              const isCompleted =
                savedStatus === "completed";

              const isPartial =
                savedStatus === "partial"
                || savedStatus === "in_progress";

              const previousLessonsCompleted =
                lessons
                  .slice(0, index)
                  .every(
                    previousLesson =>
                      String(
                        progressByLessonId.get(Number(previousLesson?.id || 0))?.status
                        || "not_started"
                      ) === "completed"
                  );

              const isNext =
                !isCompleted
                && !isPartial
                && previousLessonsCompleted;

              const stateClass =
                isCompleted
                  ? "completed"
                  : isPartial
                    ? "partial"
                    : isNext
                      ? "next"
                      : "locked";

              const status =
                isCompleted
                  ? (
                      order === currentOrder
                        ? `הושלם • ${score}%`
                        : "הושלם ✓"
                    )
                  : isPartial
                    ? "התחלת את השיעור • אפשר להמשיך"
                    : isNext
                      ? "השיעור הבא"
                      : "טרם נפתח 🔒";

              const button =
                isNext
'''
if old not in text:
    raise SystemExit('cards state block not found')
text = text.replace(old, new, 1)

old = '''  const phase =
    String(
      window.CURRENT_LESSON_FLOW_PHASE
      || "explanation"
    );

  const currentLessonCompleted =
    phase === "summary"
    || phase === "next";

  const completedCount =
    Math.max(
      0,
      Math.min(
        totalLessons,
        currentOrder - 1 + (currentLessonCompleted ? 1 : 0)
      )
    );
'''
new = '''  const savedProgressRows =
    Array.isArray(window.LESSON_SIDEBAR_PROGRESS_ROWS)
      ? window.LESSON_SIDEBAR_PROGRESS_ROWS
      : [];

  const completedIds =
    new Set(
      savedProgressRows
        .filter(row => String(row?.status || "") === "completed")
        .map(row => Number(row?.unit_lesson_id || 0))
    );

  const completedCount =
    lessons.filter(
      lesson => completedIds.has(Number(lesson?.id || 0))
    ).length;
'''
if old not in text:
    raise SystemExit('gauge block not found')
text = text.replace(old, new, 1)

# Add partial card styling via JS style injector, avoiding CSS file changes.
marker = "    .lesson-ai-waiting-status{position:relative;z-index:5;"
insert = '''    .lesson-completion-card.partial{border-color:rgba(242,189,85,.55)!important;box-shadow:inset 0 0 0 1px rgba(242,189,85,.10)!important;}
    .lesson-completion-card.partial .lesson-completion-card-status{color:#f2bd55!important;}
'''
if marker not in text:
    raise SystemExit('style marker not found')
text = text.replace(marker, insert + marker, 1)
p.write_text(text, encoding='utf-8')

p2 = Path('he/workspace/index.html')
idx = p2.read_text(encoding='utf-8')
idx = idx.replace('IAKIDS • build 0.5.7', 'IAKIDS • build 0.5.8')
idx = idx.replace('window.IAKIDS_BUILD_VERSION = "0.5.7";', 'window.IAKIDS_BUILD_VERSION = "0.5.8";')
p2.write_text(idx, encoding='utf-8')
