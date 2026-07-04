# Contributing to NetPulse

First off, thanks for taking the time to contribute!

The following is a set of guidelines for contributing to NetPulse. These are mostly guidelines, not rules. Use your best judgment, and feel free to propose changes to this document in a pull request.

## How Can I Contribute?

### Reporting Bugs
This section guides you through submitting a bug report for NetPulse. Following these guidelines helps maintainers understand your report, reproduce the behavior, and find related reports.

* **Use a clear and descriptive title** for the issue to identify the problem.
* **Describe the exact steps** which reproduce the problem in as many details as possible.
* **Provide specific examples** to demonstrate the steps. Include links to files or copy/paste snippets.

### Suggesting Enhancements
* **Explain why this enhancement would be useful** to most NetPulse users.
* **Detail the exact implementation** you would prefer.

### Pull Requests
1. **Fork the repo** and create your branch from `main`.
2. **Install dependencies** for both the frontend (`npm install`) and backend (`pip install -e .`).
3. **Ensure tests pass** before pushing. Run `pytest` for the backend and `npm run test:e2e` for the frontend.
4. **Follow the architectural rules**. For example, the backend utilizes the Repository Pattern. Do not put raw SQL inside FastApi route handlers.
5. **Issue that pull request!**

## Styleguides

### Git Commit Messages
* Use the present tense ("Add feature" not "Added feature").
* Use the imperative mood ("Move cursor to..." not "Moves cursor to...").
* Limit the first line to 72 characters or less.
* Reference issues and pull requests liberally after the first line.

### TypeScript
* **No `any` types allowed.** Ever. If you must, use `unknown` and perform type narrowing.
* Follow the exact Next.js App Router conventions (server vs client components).

### Python
* Follow `PEP 8`.
* Use type hints for everything. We enforce strict MyPy typing.
* Follow SOLID principles and stick to the Clean Architecture implemented.

---
By contributing to NetPulse, you agree that your contributions will be licensed under its MIT License.
