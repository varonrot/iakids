'use strict';

// This module is server-side preparation for the English lesson engine.
// Do not put provider keys or a generated plan with answer keys in a browser response.
const INTERACTIONS = new Set(['continue', 'multiple_choice', 'tap_region', 'spoken_answer']);
const PHASES = new Set(['see_the_idea', 'try_together', 'your_turn']);

const SUBJECT_GUIDES = {
  Math: [
    'Teach one mathematical idea at a time and check the arithmetic before replying.',
    'Use a concrete representation before a shortcut or algorithm.',
    'If a prerequisite is missing, name that skill and teach it before advancing.',
    'A wrong answer gets one short, specific hint and another attempt; do not lecture or reveal the answer immediately.'
  ].join(' ')
};

const TOPIC_GUIDES = {
  'Dividing fractions': [
    'The objective of this micro-lesson is to interpret division as asking how many groups fit.',
    'For 3/4 divided by 1/2, distinguish one full half and half of another half.',
    'Check that the learner understands equal parts and equivalent fractions before using this example.',
    'Do not claim that a three-question quick check proves mastery of fractions.',
    'Do not automatically teach a reciprocal rule before the visual meaning is understood.'
  ].join(' ')
};

function buildTeacherRequest(context) {
  if (!context || !Number.isInteger(context.grade) || context.grade < 1 || context.grade > 12) {
    throw new TypeError('A valid grade is required.');
  }
  if (!SUBJECT_GUIDES[context.subject] || !TOPIC_GUIDES[context.topic]) {
    throw new TypeError('This subject and topic do not have an approved guide yet.');
  }
  if (context.language !== 'en') throw new TypeError('The English engine requires language en.');
  const available = context.availableInteractions || ['continue', 'multiple_choice'];
  if (!Array.isArray(available) || !available.length || available.some(type => !INTERACTIONS.has(type))) {
    throw new TypeError('Unsupported interaction type.');
  }
  return [
    {role:'system', content:[
      'You are an elementary-school teacher. Write in the requested lesson language.',
      'Create one short micro-lesson, not a complete course. Explain clearly, then pause at most once per beat.',
      'Choose an interaction only when it helps learning; an explanation may end with Continue instead of a quiz.',
      'Choose only from the interaction types supplied by the application.',
      'Treat a quick check as a low-confidence placement hint, never as proof of mastery.',
      'Return structured JSON only. Do not include personal information or an invented curriculum standard.'
    ].join(' ')},
    {role:'developer', content:`Subject guide: ${SUBJECT_GUIDES[context.subject]} Topic guide: ${TOPIC_GUIDES[context.topic]}`},
    {role:'user', content:JSON.stringify({
      task:'Prepare the first micro-lesson in the selected topic.',
      subject:context.subject, topic:context.topic, grade:context.grade,
      language:context.language, available_interactions:available,
      quick_check:context.quickCheck || {status:'unknown'},
      output_contract:{
        version:1, skill_id:'string', objective:'string',
        steps:[{phase:'see_the_idea | try_together | your_turn',
          teacher_text:'short text', visual:{kind:'none | generated_image', brief:'required for generated_image'},
          interaction:{type:'continue | multiple_choice | tap_region | spoken_answer',
            prompt:'optional short question', options:'required for multiple_choice, 2-4 strings',
            answer_index:'required for multiple_choice, server-only integer'}}]
      }
    })}
  ];
}

function validateTeacherPlan(plan, availableInteractions = ['continue', 'multiple_choice']) {
  const errors = [];
  if (!plan || typeof plan !== 'object' || plan.version !== 1) return {valid:false, errors:['Unsupported lesson plan version.']};
  if (typeof plan.skill_id !== 'string' || !plan.skill_id.trim()) errors.push('Missing skill_id.');
  if (typeof plan.objective !== 'string' || !plan.objective.trim()) errors.push('Missing objective.');
  if (!Array.isArray(plan.steps) || !plan.steps.length || plan.steps.length > 3) {
    errors.push('A micro-lesson needs one to three steps.');
  } else {
    const phases = new Set();
    plan.steps.forEach((step, index) => {
      if (!step || !PHASES.has(step.phase) || phases.has(step.phase)) errors.push(`Step ${index + 1} has an invalid or repeated phase.`);
      else phases.add(step.phase);
      if (typeof step.teacher_text !== 'string' || !step.teacher_text.trim()) errors.push(`Step ${index + 1} needs teacher text.`);
      if (!step.visual || !['none', 'generated_image'].includes(step.visual.kind) ||
          (step.visual.kind === 'generated_image' && (typeof step.visual.brief !== 'string' || !step.visual.brief.trim()))) {
        errors.push(`Step ${index + 1} has an invalid visual request.`);
      }
      const action = step.interaction;
      if (!action || !INTERACTIONS.has(action.type) || !availableInteractions.includes(action.type)) {
        errors.push(`Step ${index + 1} has an unsupported interaction.`);
      } else if (action.type === 'multiple_choice') {
        if (typeof action.prompt !== 'string' || !action.prompt.trim() || !Array.isArray(action.options) ||
            action.options.length < 2 || action.options.length > 4 ||
            action.options.some(option => typeof option !== 'string' || !option.trim()) ||
            new Set(action.options).size !== action.options.length ||
            !Number.isInteger(action.answer_index) || action.answer_index < 0 || action.answer_index >= action.options.length) {
          errors.push(`Step ${index + 1} has invalid multiple-choice data.`);
        }
      } else if (action.type !== 'continue' && (typeof action.prompt !== 'string' || !action.prompt.trim())) {
        errors.push(`Step ${index + 1} needs an interaction prompt.`);
      }
    });
  }
  return {valid:errors.length === 0, errors};
}

module.exports = {buildTeacherRequest, validateTeacherPlan};
