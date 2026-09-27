'use strict';
const test = require('node:test');
const assert = require('node:assert/strict');
const {buildTeacherRequest, validateTeacherPlan} = require('./teacher-plan');

const context = {subject:'Math', topic:'Dividing fractions', grade:5, language:'en',
  availableInteractions:['continue', 'multiple_choice'], quickCheck:{status:'placement_hint', answered:3, correct:2}};

test('subject and topic guides are combined in one OpenAI request', () => {
  const messages = buildTeacherRequest(context);
  assert.equal(messages.length, 3);
  assert.match(messages[1].content, /Subject guide:.*Topic guide:/);
  assert.match(messages[0].content, /never as proof of mastery/);
  assert.equal(JSON.parse(messages[2].content).quick_check.status, 'placement_hint');
});

test('one explanatory step can ask only for Continue', () => {
  const plan = {version:1, skill_id:'division-as-groups', objective:'Count groups visually',
    steps:[{phase:'see_the_idea', teacher_text:'What does one half mean?',
      visual:{kind:'generated_image', brief:'Three of four equal parts'}, interaction:{type:'continue'}}]};
  assert.deepEqual(validateTeacherPlan(plan), {valid:true, errors:[]});
});

test('unsupported input and malformed answers are rejected before display', () => {
  const plan = {version:1, skill_id:'division-as-groups', objective:'Count groups visually',
    steps:[{phase:'your_turn', teacher_text:'Try it.', visual:{kind:'none'},
      interaction:{type:'multiple_choice', prompt:'How many?', options:['1', '2', '2'], answer_index:4}}]};
  assert.equal(validateTeacherPlan(plan).valid, false);
  plan.steps[0].interaction = {type:'spoken_answer', prompt:'Tell me why.'};
  assert.equal(validateTeacherPlan(plan).valid, false);
});

test('English engine rejects unknown subjects and grades', () => {
  assert.throws(() => buildTeacherRequest({...context, grade:0}), /grade/);
  assert.throws(() => buildTeacherRequest({...context, subject:'Science'}), /approved guide/);
});
