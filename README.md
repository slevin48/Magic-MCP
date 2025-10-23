# Magic-MCP

Magic square function served as a MCP 🪄✨

## Getting started

1. Create a virtual environment and install the dependencies:

   ```bash
   python -m venv .venv
   source .venv/bin/activate
   pip install -r requirements.txt
   ```

2. Run the MCP server:

   ```bash
   python -m magic_mcp.server
   ```

   The server exposes a single tool, `generate_magic_square`, which proxies a
   remote MATLAB service hosted at
   `https://matlab-0j1h.onrender.com/mymagic/mymagic`.

3. Connect an MCP-compatible client to the server (for example, via MCP
   discovery or by pointing the client at the stdio endpoint) and invoke the
   `generate_magic_square` tool. Provide the desired square size (and optionally
   set `debug=true`) to receive a structured response containing both the magic
   square and the raw metadata returned by the upstream service.
