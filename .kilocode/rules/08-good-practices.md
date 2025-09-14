# Good Practices – Jobs Manager Backend (Python/Django)

## SOLID Principles

- **Single Responsibility Principle (SRP):** Each module, class, or function should have only one reason to change.
- **Open/Closed Principle (OCP):** Classes and functions should be open for extension, but closed for modification.
- **Liskov Substitution Principle (LSP):** Subclasses must be substitutable for their base classes without breaking the application.
- **Interface Segregation Principle (ISP):** Prefer small, focused interfaces (abstract base classes, protocols) over large, general ones.
- **Dependency Inversion Principle (DIP):** Depend on abstractions, not on concrete implementations (use dependency injection, service layers).

## Avoid Deep Nesting

- Limit nesting to 2-3 levels per function/method.
- Use early returns and guard clauses to reduce indentation.
- Split complex logic into smaller, well-named functions or methods.

## Prefer Match-Case (Python 3.10+) or Dict Mapping Over Multiple Ifs

- For multiple conditions on the same variable, use `match-case` (Python 3.10+) or a dictionary mapping instead of chained `if-elif-else` blocks.
- This improves readability and maintainability.

```python
# Prefer this (Python 3.10+):
match status:
    case 'draft':
        ...
    case 'active':
        ...
    case _:
        ...

# Or with dict mapping:
actions = {
    'draft': handle_draft,
    'active': handle_active,
}
actions.get(status, handle_default)()

# Instead of:
if status == 'draft':
    ...
elif status == 'active':
    ...
else:
    ...
```

## Objects Calisthenics (Pythonic Version)

- Only one level of indentation per function/method.
- Avoid `else` by using early returns.
- Wrap primitives and strings in value objects or dataclasses when possible.
- Use first-class collections (custom classes, QuerySets) instead of raw lists/dicts.
- One dot per line: avoid chaining too many calls (e.g., `obj.a.b.c.d`).
- Use clear, descriptive names (no abbreviations).
- Keep classes, functions, and files small and focused.

## Clean Code

- Write code for humans: prioritize readability and clarity.
- Use meaningful names for variables, functions, and classes.
- Keep functions and files short and focused.
- Remove dead code and unnecessary comments.
- Prefer composition over inheritance.
- Avoid magic numbers and hardcoded values; use constants.
- Write self-explanatory code; comments should explain "why", not "what".
- Use type hints and docstrings for clarity.

## Clean Architecture

- Separate concerns: views, business logic (services), and data access (repositories/models) should be in distinct layers.
- Use dependency injection for services and repositories (pass dependencies as arguments).
- Keep business logic independent from Django and frameworks when possible.
- Favor composition and modularity for testability and maintainability.
- Use boundaries (interfaces, adapters) to decouple layers.

---

**References:**

- [SOLID Principles](https://en.wikipedia.org/wiki/SOLID)
- [Object Calisthenics](https://williamdurand.fr/2013/06/03/object-calisthenics/)
- [Clean Code (Robert C. Martin)](https://www.oreilly.com/library/view/clean-code/9780136083238/)
- [Clean Architecture (Robert C. Martin)](https://www.oreilly.com/library/view/clean-architecture/9780134494272/)
- [PEP 8 – Style Guide for Python Code](https://peps.python.org/pep-0008/)
- [PEP 257 – Docstring Conventions](https://peps.python.org/pep-0257/)
