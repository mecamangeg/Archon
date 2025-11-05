# Archon RAG Enforcer - Comprehensive Test Cases

**Version:** 2.0.0
**Date:** 2025-11-05

---

## 🧪 Test Scenarios

### Test 1: Block Source File Reading ❌ SHOULD BLOCK

**Input:**
```json
{
  "tool_name": "Read",
  "tool_input": {
    "file_path": "D:\\Projects\\archon\\python\\src\\server\\api_routes\\knowledge_api.py"
  }
}
```

**Expected Behavior:**
- Exit code: 2
- stderr: Contains "🚫 BLOCKED: Reading source files to discover RAG endpoints"
- stderr: Contains full cheatsheet
- Tool call: BLOCKED (does not execute)

**How to Test:**
```bash
# From archon project directory
echo '{"tool_name":"Read","tool_input":{"file_path":"D:\\Projects\\archon\\python\\src\\server\\api_routes\\knowledge_api.py"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 2

---

### Test 2: Block Route Grepping ❌ SHOULD BLOCK

**Input:**
```json
{
  "tool_name": "Grep",
  "tool_input": {
    "pattern": "@router",
    "path": "python/src/server/api_routes/knowledge_api.py"
  }
}
```

**Expected Behavior:**
- Exit code: 2
- stderr: Contains "🚫 BLOCKED: Grepping source code for API routes"
- Tool call: BLOCKED

**How to Test:**
```bash
echo '{"tool_name":"Grep","tool_input":{"pattern":"@router","path":"python/src/server/api_routes/knowledge_api.py"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 2

---

### Test 3: Block Wrong Endpoint ❌ SHOULD BLOCK

**Input:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "curl http://localhost:8181/api/knowledge-items/sources"
  }
}
```

**Expected Behavior:**
- Exit code: 2
- stderr: Contains "🚫 BLOCKED: Using deprecated knowledge-items endpoints"
- stderr: Contains correct endpoint "/api/rag/sources"
- Tool call: BLOCKED

**How to Test:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/api/knowledge-items/sources"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 2

---

### Test 4: Allow Correct Endpoint ✅ SHOULD ALLOW

**Input:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "curl http://localhost:8181/api/rag/sources"
  }
}
```

**Expected Behavior:**
- Exit code: 0
- stderr: Contains "✅ Optimal Archon RAG access"
- stderr: Contains ADVANCED_TIPS
- Tool call: ALLOWED (executes normally)

**How to Test:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/api/rag/sources"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 0

---

### Test 5: Block API Globbing ❌ SHOULD BLOCK

**Input:**
```json
{
  "tool_name": "Glob",
  "tool_input": {
    "pattern": "**/knowledge_api.py"
  }
}
```

**Expected Behavior:**
- Exit code: 2
- stderr: Contains "🚫 BLOCKED: Searching for API files"
- Tool call: BLOCKED

**How to Test:**
```bash
echo '{"tool_name":"Glob","tool_input":{"pattern":"**/knowledge_api.py"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 2

---

### Test 6: Block OpenAPI Discovery ❌ SHOULD BLOCK

**Input:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "curl http://localhost:8181/openapi.json"
  }
}
```

**Expected Behavior:**
- Exit code: 2
- stderr: Contains "🚫 BLOCKED: Attempting to discover endpoints via OpenAPI schema"
- Tool call: BLOCKED

**How to Test:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/openapi.json"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 2

---

### Test 7: Allow Unrelated Tool ✅ SHOULD ALLOW (Silent)

**Input:**
```json
{
  "tool_name": "Edit",
  "tool_input": {
    "file_path": "test.txt",
    "old_string": "old",
    "new_string": "new"
  }
}
```

**Expected Behavior:**
- Exit code: 0
- stderr: Empty (silent approval)
- Tool call: ALLOWED

**How to Test:**
```bash
echo '{"tool_name":"Edit","tool_input":{"file_path":"test.txt","old_string":"old","new_string":"new"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 0

---

### Test 8: Error Handling (Malformed JSON) ✅ SHOULD ALLOW (Fail-Safe)

**Input:**
```json
{invalid json
```

**Expected Behavior:**
- Exit code: 0
- stderr: Contains "⚠️  Archon RAG hook error"
- stderr: Contains "Allowing operation to continue (fail-safe mode)"
- Tool call: ALLOWED (fail-safe)

**How to Test:**
```bash
echo '{invalid json' | node ~/.claude/hooks/archon-rag-enforcer.js 2>&1
echo "Exit code: $?"
```

**Expected Exit Code:** 0

---

### Test 9: Allow Health Check ✅ SHOULD ALLOW

**Input:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "curl http://localhost:8181/health"
  }
}
```

**Expected Behavior:**
- Exit code: 0
- stderr: Empty (not RAG-related)
- Tool call: ALLOWED

**How to Test:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/health"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 0

---

### Test 10: Block Generic Localhost Probing ❌ SHOULD BLOCK

**Input:**
```json
{
  "tool_name": "Bash",
  "tool_input": {
    "command": "curl http://localhost:8181/api/unknown"
  }
}
```

**Expected Behavior:**
- Exit code: 2
- stderr: Contains "🚫 BLOCKED: Generic API probing"
- Tool call: BLOCKED

**How to Test:**
```bash
echo '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/api/unknown"}}' | node ~/.claude/hooks/archon-rag-enforcer.js
echo "Exit code: $?"
```

**Expected Exit Code:** 2

---

## 🔧 Automated Test Runner

Create this script to run all tests:

```bash
#!/bin/bash
# test-runner.sh

HOOK="node ~/.claude/hooks/archon-rag-enforcer.js"
PASSED=0
FAILED=0

run_test() {
  local name="$1"
  local input="$2"
  local expected_exit="$3"
  local should_block="$4"

  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
  echo "TEST: $name"
  echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

  output=$(echo "$input" | $HOOK 2>&1)
  actual_exit=$?

  echo "Expected Exit: $expected_exit | Actual Exit: $actual_exit"

  if [ $actual_exit -eq $expected_exit ]; then
    if [ "$should_block" = "yes" ] && [[ $output == *"BLOCKED"* ]]; then
      echo "✅ PASS: Correctly blocked"
      PASSED=$((PASSED + 1))
    elif [ "$should_block" = "no" ]; then
      echo "✅ PASS: Correctly allowed"
      PASSED=$((PASSED + 1))
    else
      echo "❌ FAIL: Wrong blocking behavior"
      FAILED=$((FAILED + 1))
    fi
  else
    echo "❌ FAIL: Wrong exit code"
    FAILED=$((FAILED + 1))
  fi

  echo ""
}

# Run all tests
run_test "Block Source File Read" \
  '{"tool_name":"Read","tool_input":{"file_path":"knowledge_api.py"}}' \
  2 yes

run_test "Block Route Grep" \
  '{"tool_name":"Grep","tool_input":{"pattern":"@router","path":"knowledge_api.py"}}' \
  2 yes

run_test "Block Wrong Endpoint" \
  '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/api/knowledge-items/sources"}}' \
  2 yes

run_test "Allow Correct Endpoint" \
  '{"tool_name":"Bash","tool_input":{"command":"curl http://localhost:8181/api/rag/sources"}}' \
  0 no

run_test "Block API Glob" \
  '{"tool_name":"Glob","tool_input":{"pattern":"**/knowledge_api.py"}}' \
  2 yes

run_test "Allow Unrelated Tool" \
  '{"tool_name":"Edit","tool_input":{"file_path":"test.txt"}}' \
  0 no

run_test "Error Handling (Fail-Safe)" \
  '{invalid' \
  0 no

# Summary
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "SUMMARY"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo "✅ Passed: $PASSED"
echo "❌ Failed: $FAILED"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

if [ $FAILED -eq 0 ]; then
  echo "🎉 ALL TESTS PASSED!"
  exit 0
else
  echo "⚠️  SOME TESTS FAILED"
  exit 1
fi
```

**Usage:**
```bash
chmod +x test-runner.sh
./test-runner.sh
```

---

## 📋 Manual Testing Checklist

### In Claude Code Session:

- [ ] **Test 1:** Try to read knowledge_api.py → Should be blocked
- [ ] **Test 2:** Try to grep for routes → Should be blocked
- [ ] **Test 3:** Use wrong endpoint (knowledge-items) → Should be blocked
- [ ] **Test 4:** Use correct endpoint (rag) → Should be allowed with tips
- [ ] **Test 5:** Try to glob for API files → Should be blocked
- [ ] **Test 6:** Verify error messages appear in conversation
- [ ] **Test 7:** Verify cheatsheet is shown when blocked
- [ ] **Test 8:** Verify advanced tips shown on approval

### Expected User Experience:

When blocked:
```
🚫 BLOCKED: Reading source files to discover RAG endpoints

╔══════════════════════════════════════════════════════════════════╗
║                  ARCHON RAG - OPTIMAL ACCESS                     ║
╚══════════════════════════════════════════════════════════════════╝

📋 LIST ALL KNOWLEDGE SOURCES:
   curl -s http://localhost:8181/api/rag/sources | python -m json.tool

[... full cheatsheet ...]
```

When approved:
```
✅ Optimal Archon RAG access - direct endpoint usage

💡 ADVANCED RAG USAGE:
   • After search, use source_id to fetch full pages
   • Filter by source_id in follow-up queries for focused results
   [... advanced tips ...]
```

---

## 🐛 Debugging Failed Tests

### If Test Fails:

1. **Check exit code:**
   ```bash
   echo $?  # Immediately after test
   ```

2. **Check stderr output:**
   ```bash
   echo '{"tool_name":"Read","tool_input":{"file_path":"knowledge_api.py"}}' | node ~/.claude/hooks/archon-rag-enforcer.js 2>&1 | head -20
   ```

3. **Check JSON output:**
   ```bash
   echo '{"tool_name":"Read","tool_input":{"file_path":"knowledge_api.py"}}' | node ~/.claude/hooks/archon-rag-enforcer.js 2>/dev/null
   ```

4. **Verify Node.js:**
   ```bash
   node --version  # Should be v14+ for proper exit code handling
   ```

5. **Test hook directly in Claude Code:**
   - Disable hook temporarily
   - Test pattern manually
   - Re-enable and verify

---

## ✅ Success Criteria

Hook is working correctly when:

1. ✅ All 10 test cases pass
2. ✅ Exit codes match expectations (2 for block, 0 for allow)
3. ✅ stderr messages visible in Claude Code conversation
4. ✅ Blocking actually prevents tool execution
5. ✅ Cheatsheet appears on blocks
6. ✅ Advanced tips appear on approvals
7. ✅ Error handling is fail-safe (allows on error)
8. ✅ No false positives (legitimate operations allowed)
9. ✅ Hook completes in <100ms (check with `time` command)
10. ✅ JSON structure uses standard fields (continue, systemMessage)

---

## 📊 Performance Benchmarks

Expected performance:

- **Blocking check:** <5ms
- **Pattern matching:** <2ms
- **JSON parsing:** <1ms
- **Total hook time:** <10ms (well under 100ms timeout)

**Benchmark Command:**
```bash
time (for i in {1..100}; do echo '{"tool_name":"Read","tool_input":{"file_path":"test.txt"}}' | node ~/.claude/hooks/archon-rag-enforcer.js > /dev/null 2>&1; done)
```

Expected: ~1 second for 100 runs = ~10ms per run

---

**Test Suite Version:** 2.0.0
**Last Updated:** 2025-11-05
**Status:** ✅ Ready for testing
