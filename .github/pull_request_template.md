## 📝 Description

_One or two sentences summarizing what this PR does and why._

## 🔗 Related Issue

Closes #[issue-number]

## 🚀 Changes

- Brief bullet-list of the main changes (e.g. added `ChatMessageSerializer`, moved logic to `services/chat.py`, introduced pagination).
- …

## ✅ Checklist

**Django REST Framework**
- [ ] I used a `Serializer` for all request/response payloads
- [ ] Business logic is isolated in a service layer (`services/…`)
- [ ] Query optimizations (`select_related`/`prefetch_related`) applied where needed
- [ ] Pagination and filtering are configured for list endpoints
- [ ] Permissions and authentication classes are correct
- [ ] Error handling is uniform (all errors return JSON with a `detail` field)

**General**
- [ ] Code is type-hinted and passes `tox -e mypy`
- [ ] Formatted with Black/isort and linted with Flake8 (`tox -e lint`)
- [ ] Covered by new or updated unit tests
- [ ] Docstrings follow Google or NumPy style
