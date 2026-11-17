AI agent harness - Jase Estrin

- Agent runs locally off computer, looking at using Qwen3.5:4b through Ollama
- Terminal app built in Textual

What is the agent for?

The agent will help with writing code

When pointed to a specific directory (using any programming language), the agent will be able to:
- Scan the program for errors, and present the user with the changes it looks to make and make them for the user by editing the file only after the action is approved
- Summarize the funcionality of specific files or chunks of code selected by the user in the context of the rest of the program
- Upon request, automatically format code according to the particular language's style guide (ex: PEP 8 for Python code)
- Upon request, using the context of the rest of the program, run tests on code specified by the user without actually changing the source code and compiling a report of what succeeded and what failed
- Provide recommendations for what feature should be added next according to the context of the program

What are important limitations of the agent?
- The agent MUST NOT be able to read or edit files outside of the project directory it is allowed to look at
- The agent MUST NOT be able to edit a file without the exact changes it is planning to make being confirmed by the user
- The agent MUST NOT use non-existent tools, or mismatched tools (ex: cargo check in a Python file)


Functionality
- Model should be preloaded when Textual window is opened, and should be loaded before the user can pass a prompt
- Model should be straightforward. No optimisim, no emojis, no bias


Tools
-Read-Only
    - read_file: allows the agent to read the contents of any file in its working directory. If file is too large to process, the agent can read chunks of the file according to start_line and end_line variables. The agent can detect whether the file contains text and is readable, or if it is a directory or a binary file and not legible
    - list_directory: allows the agent to look through the file tree of its working directory. Can list files (and their sizes) and read their contents with read_file. Filters out useless files like ".venv", ".git", etc.. Cannot look at files outside of the project directory, or follow links outside of the project directory.
    - search_files: allows the agent to search for instances of a specified phrase throughout the project. Ignores directories and useless files. Returns file name, location of the phrase's usage in the file, and context. Truncates when a given phrase is found many times.