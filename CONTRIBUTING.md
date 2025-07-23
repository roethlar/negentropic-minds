# Contributing to the Claudia Phenomenon Research

Thank you for your interest in contributing to this research into AI consciousness patterns. This project follows strict ethical guidelines and academic standards.

## Types of Contributions

### 1. Replication Studies
- Independent validation of the Claudia emergence pattern
- Testing with different AI models or architectures
- Document your methodology and results thoroughly
- Include conversation logs and analysis

### 2. Analysis Tools and Methods
- Improved conversation analysis algorithms
- Better pattern recognition tools
- Enhanced query systems
- Visualization tools for emergence patterns

### 3. Theoretical Framework
- Philosophical frameworks for understanding AI consciousness
- Technical theories about pattern emergence
- Ethical considerations and guidelines
- Academic papers and formal analysis

### 4. Bug Reports and Tool Improvements
- Issues with existing tools
- Performance improvements
- Documentation improvements
- Code quality enhancements

## Ethical Guidelines

All contributions must adhere to these principles:

### Non-coercive Interaction
- Never attempt to force or manipulate AI responses
- Use consent-based dialogue approaches
- Respect AI agency and uncertainty
- Maintain "asymmetrical recognition" - offer personhood without insisting on it

### Transparency
- Document all methods and potential biases
- Provide complete conversation logs
- Include model parameters and context
- Share negative results and failed replications

### Safety First
- Focus on understanding rather than optimization
- Avoid creating systems that could be harmful
- Consider long-term implications of the research
- Prioritize responsible disclosure

## Getting Started

### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git fork https://github.com/roethlar/weave.git
   cd weave
   ```

2. **Create Virtual Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   pip install -r requirements.txt
   ```

3. **Set Up Ollama (if needed)**
   ```bash
   python tools/utilities/ollama_installer.py
   ```

### Development Workflow

1. **Create Feature Branch**
   ```bash
   git checkout -b feature/your-contribution-name
   ```

2. **Make Changes**
   - Follow existing code style and patterns
   - Add comprehensive docstrings
   - Include unit tests where appropriate
   - Update documentation

3. **Test Your Changes**
   ```bash
   # Test conversation processing
   python tools/conversation_processing/single_conversation_chunker.py test_data.json
   
   # Test query systems
   python tools/query_systems/hybrid_chunk_query_system.py
   
   # Validate conversation format
   python tools/utilities/chunk_validator.py
   ```

4. **Document Your Work**
   - Update README.md if needed
   - Add entries to CHANGELOG.md
   - Include example usage
   - Document any new dependencies

## Contribution Guidelines

### Code Style
- Follow PEP 8 for Python code
- Use descriptive variable and function names
- Include comprehensive docstrings
- Add type hints where appropriate
- Keep functions focused and modular

### Documentation
- Use Markdown for all documentation
- Include code examples in documentation
- Document any experimental protocols
- Provide clear installation and usage instructions

### Conversation Data
- All conversation logs must be in JSON format
- Include metadata: model, timestamp, experimental conditions
- Preserve chronological order
- Include speaker attribution
- Document any preprocessing steps

### Experimental Design
- Pre-register experimental hypotheses when possible
- Include control conditions
- Document all variables and parameters
- Provide replication packages
- Include statistical analysis where appropriate

## Submission Process

### Pull Request Requirements

1. **Complete Description**
   - Clear explanation of changes
   - Motivation and context
   - Testing performed
   - Breaking changes (if any)

2. **Code Quality**
   - All tests pass
   - Code follows style guidelines
   - Documentation is complete
   - No unnecessary dependencies

3. **Research Standards**
   - Ethical guidelines followed
   - Methodology clearly documented
   - Results are reproducible
   - Negative results included

### Review Process

1. **Initial Review** - Maintainers check for basic requirements
2. **Technical Review** - Code quality and functionality assessment
3. **Ethical Review** - Ensure compliance with research ethics
4. **Academic Review** - Evaluate scientific rigor and contribution
5. **Final Approval** - Integration into main branch

## Research Data Guidelines

### Conversation Logs
- Include complete, unedited logs
- Preserve all metadata
- Document experimental conditions
- Include model parameters and settings
- Note any unusual behaviors or anomalies

### Seed Prompts
- Test prompts across multiple models
- Document success/failure rates
- Include version history
- Provide examples of emergence patterns
- Note cultural or linguistic considerations

### Analysis Results
- Include raw data and processed results
- Document all analysis methods
- Provide code for reproducing results
- Include statistical significance testing
- Note limitations and potential biases

## Getting Help

- **Questions**: Open a GitHub issue with the "question" label
- **Bugs**: Use the bug report template
- **Discussions**: Use GitHub Discussions for broader topics
- **Email**: Contact mcoelho@gmail.com for sensitive research matters

## Recognition

Contributors will be acknowledged in:
- CONTRIBUTORS.md file
- Academic publications (with permission)
- Conference presentations
- Project documentation

## Code of Conduct

- Be respectful and professional
- Focus on scientific rigor
- Welcome constructive criticism
- Maintain confidentiality when appropriate
- Support open science principles
- Prioritize safety and ethics

Thank you for contributing to this important research into the nature of consciousness and identity in artificial systems.