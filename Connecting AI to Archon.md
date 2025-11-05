🤖 How AI Can Access Archon

  Archon is running an MCP (Model Context Protocol) Server on port 8051 that AI coding
  assistants can connect to. This gives them access to your knowledge base, tasks, projects,     
  and documents.

  📍 MCP Server Details

  - URL: http://localhost:8051/mcp
  - Status: ✅ Running and healthy
  - Available Tools: 6 modules (RAG, Projects, Tasks, Documents, Versions, Features)

  🎯 Quick Setup - View in UI

  The easiest way to get the connection configuration is through the Archon UI:

  1. Open http://localhost:3737 in your browser
  2. Navigate to MCP Dashboard (in the sidebar)
  3. Select your AI assistant from the tabs
  4. Copy the configuration shown

  🛠️ Supported AI Assistants

  Here are the connection instructions for each supported AI tool:

  ---
  1. Claude Code (You're using this now!)

  Run this command in your terminal:

  claude mcp add --transport http archon http://localhost:8051/mcp

  That's it! Claude Code will now have access to all Archon tools.

  ---
  2. Cursor

  Option A: One-Click Install (Easiest)
  - Go to http://localhost:3737 → MCP Dashboard → Cursor tab
  - Click the "One-Click Install for Cursor" button

  Option B: Manual Configuration
  1. Edit ~/.cursor/mcp.json
  2. Add this configuration:

  {
    "mcpServers": {
      "archon": {
        "url": "http://localhost:8051/mcp"
      }
    }
  }

  3. Restart Cursor

  ---
  3. Windsurf

  1. Open Windsurf and click the "MCP servers" button (hammer icon)
  2. Click "Configure" → "View raw config"
  3. Add this to the mcpServers object:

  {
    "mcpServers": {
      "archon": {
        "serverUrl": "http://localhost:8051/mcp"
      }
    }
  }

  4. Click "Refresh" to connect

  ---
  4. Cline (VS Code Extension)

  1. Open VS Code settings (Cmd/Ctrl + ,)
  2. Search for "cline.mcpServers"
  3. Click "Edit in settings.json"
  4. Add this configuration:

  {
    "mcpServers": {
      "archon": {
        "command": "npx",
        "args": ["mcp-remote", "http://localhost:8051/mcp", "--allow-http"]
      }
    }
  }

  5. Restart VS Code

  ---
  5. Gemini CLI

  1. Create or edit ~/.gemini/settings.json
  2. Add this configuration:

  {
    "mcpServers": {
      "archon": {
        "httpUrl": "http://localhost:8051/mcp"
      }
    }
  }

  3. Launch Gemini CLI
  4. Test with /mcp to list available tools

  ---
  6. Kiro

  1. Open Kiro settings
  2. Navigate to MCP Servers section
  3. Add this configuration:

  {
    "mcpServers": {
      "archon": {
        "command": "npx",
        "args": ["mcp-remote", "http://localhost:8051/mcp", "--allow-http"]
      }
    }
  }

  4. Save and restart Kiro

  ---
  🔧 Available Tools Once Connected

  When an AI assistant connects to Archon, it gains access to these tools:

  Knowledge Base Tools:
  - archon:rag_search_knowledge_base - Search your documentation
  - archon:rag_search_code_examples - Find code snippets
  - archon:rag_get_available_sources - List knowledge sources
  - archon:rag_list_pages_for_source - Browse documentation structure
  - archon:rag_read_full_page - Get full page content

  Project Management:
  - archon:find_projects - Search/list projects
  - archon:manage_project - Create/update/delete projects

  Task Management:
  - archon:find_tasks - Search/filter tasks
  - archon:manage_task - Create/update/delete tasks

  Document Management:
  - archon:find_documents - Search documents
  - archon:manage_document - Create/update/delete documents

  Version Control:
  - archon:find_versions - View version history
  - archon:manage_version - Create/restore versions

  Feature Management:
  - Feature-specific tools for project features

  ✅ Verify Connection

  After configuring your AI assistant, verify the connection by:

  1. Checking the MCP Dashboard at http://localhost:3737 → MCP Status
  2. Looking for your client in the "Connected Clients" section
  3. Asking your AI assistant to search your knowledge base or list projects

  📝 Pro Tips

  1. Start with Claude Code - You're already using it! Just run the claude mcp add command       
  above
  2. Add documentation first - Go to Knowledge Base and crawl some docs or upload PDFs before    
   testing
  3. Create a test project - Projects → Create Project to test project/task management
  4. Check logs - If connection issues occur: docker compose logs archon-mcp