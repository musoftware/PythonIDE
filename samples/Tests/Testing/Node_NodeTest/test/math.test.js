const { describe, it, test } = require('node:test');
const assert = require('node:assert');
const { add, isEven } = require('../math');

describe('add', () => {
  it('adds two numbers', () => {
    assert.strictEqual(add(2, 3), 5);
  });
  it('fails on purpose', () => {
    assert.strictEqual(add(2, 2), 5);
  });
});

test('isEven', () => {
  assert.ok(isEven(4));
});
