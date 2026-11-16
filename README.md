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