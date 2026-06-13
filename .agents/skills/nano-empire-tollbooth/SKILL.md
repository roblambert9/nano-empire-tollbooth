```markdown
# nano-empire-tollbooth Development Patterns

> Auto-generated skill from repository analysis

## Overview
This skill provides guidance on the development patterns used in the `nano-empire-tollbooth` Python codebase. It covers file organization, code style, import/export conventions, and testing patterns. While no specific frameworks or automated workflows are detected, this guide will help you contribute code that matches the project's established practices.

## Coding Conventions

### File Naming
- Use **snake_case** for all Python files.
  - Example: `tollbooth_manager.py`, `user_utils.py`

### Import Style
- Use **relative imports** within the package.
  - Example:
    ```python
    from .user_utils import get_user_id
    ```

### Export Style
- Use **named exports** for functions and classes.
  - Example:
    ```python
    def calculate_toll(amount):
        # logic here
        return amount * 0.1

    class TollBooth:
        pass
    ```

### Commit Messages
- Freeform style, no strict prefixes.
- Average commit message length: ~73 characters.
  - Example: `Fix bug in toll calculation for premium users`

## Workflows

_No automated workflows detected in this repository. Below are suggested manual workflows based on common development tasks._

### Adding a New Feature
**Trigger:** When implementing a new functionality.
**Command:** `/add-feature`

1. Create a new Python file using snake_case if needed.
2. Write your function or class with named exports.
3. Use relative imports to include any dependencies.
4. Add or update corresponding test files (`*.test.*`).
5. Commit your changes with a descriptive message.

### Fixing a Bug
**Trigger:** When resolving a reported issue or bug.
**Command:** `/fix-bug`

1. Locate the relevant file(s) using snake_case naming.
2. Apply your fix, maintaining existing code style.
3. Update or add tests to cover the bug fix.
4. Commit with a message describing the bug and the fix.

### Writing Tests
**Trigger:** When adding or updating tests.
**Command:** `/write-test`

1. Create or update a test file matching the pattern `*.test.*`.
2. Write tests for your functions or classes.
3. Use the same import/export conventions as production code.
4. Run tests using the project's preferred method (see below).

## Testing Patterns

- **Test File Pattern:** Test files are named using the pattern `*.test.*` (e.g., `tollbooth.test.py`).
- **Testing Framework:** Not explicitly detected; use standard Python testing tools (e.g., `unittest` or `pytest`) unless otherwise specified.
- **Example Test File:**
  ```python
  import unittest
  from .tollbooth_manager import calculate_toll

  class TestTollBooth(unittest.TestCase):
      def test_calculate_toll(self):
          self.assertEqual(calculate_toll(100), 10)

  if __name__ == '__main__':
      unittest.main()
  ```

## Commands
| Command       | Purpose                                 |
|---------------|-----------------------------------------|
| /add-feature  | Steps for adding a new feature          |
| /fix-bug      | Steps for fixing a bug                  |
| /write-test   | Steps for writing or updating tests     |
```