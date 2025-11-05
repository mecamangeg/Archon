#!/usr/bin/env node

/**
 * Archon RAG Access Enforcer - Best Practices Edition
 *
 * VERSION: 2.0.0 (Fixed based on Claude Code Hooks best practices)
 *
 * PHILOSOPHY: Block inefficient discovery → Force optimal direct access
 *
 * CRITICAL FIXES APPLIED:
 * - ✅ Exit code 2 for blocking (was exit 0 - bug!)
 * - ✅ stderr output for Claude visibility (was stdout)
 * - ✅ Standard JSON fields: continue, systemMessage, userMessage
 * - ✅ Fail-safe error handling (exit 0 on errors)
 * - ✅ Context injection for approved patterns
 *
 * Blocks:
 * - Reading source files to discover endpoints
 * - Grepping for routes
 * - Trial-and-error API calls
 * - Documentation diving when direct access exists
 *
 * Teaches:
 * - Exact curl commands for immediate use
 * - Zero trial-and-error tolerance
 */

const fs = require('fs');

// The canonical Archon RAG endpoints
const ARCHON_RAG_CHEATSHEET = `
╔══════════════════════════════════════════════════════════════════╗
║                  ARCHON RAG - OPTIMAL ACCESS                     ║
╚══════════════════════════════════════════════════════════════════╝

📋 LIST ALL KNOWLEDGE SOURCES:
   curl -s http://localhost:8181/api/rag/sources | python -m json.tool

🔍 SEARCH KNOWLEDGE BASE:
   curl -s -X POST http://localhost:8181/api/rag/query \\
     -H "Content-Type: application/json" \\
     -d '{"query": "your question", "top_k": 5}' | python -m json.tool

💻 SEARCH CODE EXAMPLES:
   curl -s -X POST http://localhost:8181/api/rag/code-examples \\
     -H "Content-Type: application/json" \\
     -d '{"query": "your code query"}' | python -m json.tool

📄 GET SOURCE PAGES (if you have source_id):
   curl -s "http://localhost:8181/api/rag/sources?source_id=XXX" | python -m json.tool

⚡ RULE: Use these DIRECTLY. No discovery needed. No docs needed.
`.trim();

const ADVANCED_TIPS = `
💡 ADVANCED RAG USAGE:
   • After search, use source_id to fetch full pages
   • Filter by source_id in follow-up queries for focused results
   • Combine search with code-examples for comprehensive answers
   • Use top_k parameter to control result count (default: 5)
`.trim();

// Read hook input from stdin
let inputData = '';
process.stdin.on('data', chunk => inputData += chunk);

process.stdin.on('end', () => {
  try {
    const hookInput = JSON.parse(inputData);
    const { tool_name, tool_input } = hookInput;

    // Early exit if not a tool we care about
    // ✅ Exit 0 = allow, no output needed for unrelated tools
    if (!['Bash', 'Read', 'Grep', 'Glob'].includes(tool_name)) {
      process.exit(0);
    }

    // Detection patterns for inefficient Archon RAG access
    const inefficientPatterns = [
      // Pattern 1: Reading knowledge_api.py source
      {
        name: 'source_file_read',
        detect: () =>
          tool_name === 'Read' &&
          (tool_input.file_path?.includes('knowledge_api.py') ||
           tool_input.file_path?.includes('rag_service.py') ||
           tool_input.file_path?.includes('knowledge_service.py')),
        message: 'Reading source files to discover RAG endpoints',
        severity: 'high'
      },

      // Pattern 2: Grepping for routes
      {
        name: 'route_grep',
        detect: () =>
          tool_name === 'Grep' &&
          tool_input.pattern &&
          (tool_input.pattern.includes('@router') ||
           tool_input.pattern.includes('def ') ||
           tool_input.pattern.includes('get|post|put')) &&
          (tool_input.path?.includes('knowledge') ||
           tool_input.path?.includes('rag')),
        message: 'Grepping source code for API routes',
        severity: 'high'
      },

      // Pattern 3: Globbing for API files
      {
        name: 'api_file_glob',
        detect: () =>
          tool_name === 'Glob' &&
          (tool_input.pattern?.includes('knowledge') ||
           tool_input.pattern?.includes('rag') ||
           tool_input.pattern?.includes('api')),
        message: 'Searching for API files to understand endpoints',
        severity: 'medium'
      },

      // Pattern 4: Wrong endpoints (knowledge-items instead of rag)
      {
        name: 'wrong_endpoint',
        detect: () =>
          tool_name === 'Bash' &&
          tool_input.command?.includes('curl') &&
          tool_input.command?.includes('localhost:8181') &&
          (tool_input.command?.includes('/api/knowledge/') ||
           tool_input.command?.includes('/api/knowledge-items/')),
        message: 'Using deprecated knowledge-items endpoints (use /api/rag/ instead)',
        severity: 'high'
      },

      // Pattern 5: OpenAPI/docs discovery
      {
        name: 'openapi_discovery',
        detect: () =>
          tool_name === 'Bash' &&
          tool_input.command?.includes('curl') &&
          (tool_input.command?.includes('/openapi.json') ||
           tool_input.command?.includes('/docs')),
        message: 'Attempting to discover endpoints via OpenAPI schema',
        severity: 'medium'
      },

      // Pattern 6: Generic localhost probing
      {
        name: 'generic_probe',
        detect: () =>
          tool_name === 'Bash' &&
          tool_input.command?.includes('curl') &&
          tool_input.command?.includes('localhost:8181') &&
          !tool_input.command?.includes('/api/rag/') &&
          !tool_input.command?.includes('/health') &&
          !tool_input.command?.includes('/api/mcp/'),
        message: 'Generic API probing (use specific RAG endpoints)',
        severity: 'medium'
      },

      // Pattern 7: Reading CLAUDE.md for endpoints
      {
        name: 'doc_lookup',
        detect: () =>
          tool_name === 'Read' &&
          (tool_input.file_path?.includes('CLAUDE.md') ||
           tool_input.file_path?.includes('README.md')) &&
          // Only block if we're in Archon project
          tool_input.file_path?.includes('archon'),
        message: 'Reading documentation for endpoints (use direct access)',
        severity: 'low'
      }
    ];

    // Check for inefficient patterns
    const matched = inefficientPatterns.find(p => p.detect());

    if (matched) {
      // ✅ CRITICAL: Block using exit code 2 and stderr
      const blockMessage = `
🚫 BLOCKED: ${matched.message}

${ARCHON_RAG_CHEATSHEET}

📊 EFFICIENCY METRICS:
   - Pattern Blocked: ${matched.name}
   - Severity: ${matched.severity}
   - Time Saved: ~10 seconds
   - Tokens Saved: ~500 tokens
   - Alternative: Direct API call (3 seconds, 100 tokens)

💡 WHY: The endpoints above are fixed and documented. No discovery needed.

${ADVANCED_TIPS}
      `.trim();

      // ✅ Write to stderr so Claude sees it (required for exit code 2)
      console.error(blockMessage);

      // ✅ Optional: Write structured JSON to stdout for debugging
      process.stdout.write(JSON.stringify({
        continue: false,  // ✅ Standard field (not "decision")
        systemMessage: blockMessage,
        userMessage: `Hook blocked inefficient RAG access: ${matched.name}`,
        metadata: {
          pattern: matched.name,
          severity: matched.severity,
          tool: tool_name,
          version: '2.0.0'
        }
      }, null, 2));

      // ✅ Exit code 2 = BLOCK (this is the critical fix!)
      process.exit(2);
    }

    // Allow efficient direct RAG access WITH context injection
    const isEfficientRagAccess =
      tool_name === 'Bash' &&
      tool_input.command?.includes('curl') &&
      tool_input.command?.includes('/api/rag/');

    if (isEfficientRagAccess) {
      const approvalMessage = `
✅ Optimal Archon RAG access - direct endpoint usage

${ADVANCED_TIPS}
      `.trim();

      // ✅ Write to stderr for Claude to see (optional for approval)
      console.error(approvalMessage);

      // ✅ Optional structured JSON
      process.stdout.write(JSON.stringify({
        continue: true,
        systemMessage: approvalMessage,
        metadata: {
          pattern: 'efficient_rag_access',
          tool: tool_name,
          version: '2.0.0'
        }
      }));

      // ✅ Exit 0 = allow
      process.exit(0);
    }

    // Default: approve (not related to Archon RAG)
    // ✅ Silent approval - no output needed
    process.exit(0);

  } catch (error) {
    // ✅ FAIL-SAFE: On error, allow operation and log to stderr
    console.error(`⚠️  Archon RAG hook error: ${error.message}`);
    console.error('Allowing operation to continue (fail-safe mode)');

    // ✅ Optional: Log stack trace for debugging
    console.error('Stack:', error.stack);

    // ✅ Exit 0 = allow on error (fail-safe)
    process.exit(0);
  }
});
