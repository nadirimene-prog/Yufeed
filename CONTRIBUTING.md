# Contributing to YuFeed

First off, thank you for considering contributing to YuFeed! 🎉

This document provides guidelines and workflows for contributing to the project. Following these helps us maintain code quality and make the review process smoother.

## 📋 Table of Contents

- [Code of Conduct](#code-of-conduct)
- [Getting Started](#getting-started)
- [Development Workflow](#development-workflow)
- [Coding Standards](#coding-standards)
- [Testing](#testing)
- [Documentation](#documentation)
- [Commit Message Guidelines](#commit-message-guidelines)
- [Pull Request Process](#pull-request-process)
- [Release Process](#release-process)

## Code of Conduct

This project and everyone participating in it is governed by our [Code of Conduct](CODE_OF_CONDUCT.md). By participating, you are expected to uphold this code.

## Getting Started

### Prerequisites

- Python 3.12+
- Node.js 20+
- Docker & Docker Compose
- Git

### Setting Up Development Environment

1. **Fork and Clone**
   ```bash
   git clone https://github.com/yourusername/yufeed.git
   cd yufeed
   git remote add upstream https://github.com/original/yufeed.git
   ```

2. **Setup Environment**
   ```bash
   make dev-setup
   # Or manually:
   cp .env.example .env
   # Edit .env with your configuration
   ```

3. **Start Services**
   ```bash
   make docker-up
   ```

4. **Verify Setup**
   ```bash
   make verify
   ```

## Development Workflow

### Branch Naming Convention

Format: `<type>/<description>`

Types:
- `feature/` - New features
- `bugfix/` - Bug fixes
- `hotfix/` - Critical production fixes
- `docs/` - Documentation changes
- `refactor/` - Code refactoring
- `test/` - Test additions/changes
- `chore/` - Maintenance tasks

Examples:
```bash
git checkout -b feature/gap-analysis-dashboard
git checkout -b bugfix/fix-race-condition-in-alerts
git checkout -b docs/update-api-reference
```

### Working on Changes

1. **Create a branch from `main`**
   ```bash
   git checkout main
   git pull upstream main
   git checkout -b feature/my-feature
   ```

2. **Make your changes**
   - Write code following our standards
   - Add tests for new functionality
   - Update documentation

3. **Test locally**
   ```bash
   make verify
   ```

4. **Commit your changes**
   ```bash
   git add .
   git commit -m "feat(gap-analysis): add trend analysis endpoint

   - Implements trend calculation for compliance gaps
   - Adds 30/60/90 day trend views
   - Includes historical data aggregation

   Fixes #123"
   ```

5. **Push and create PR**
   ```bash
   git push origin feature/my-feature
   ```

## Coding Standards

### Python (Backend)

We follow PEP 8 with some modifications:

- **Line length**: 100 characters
- **Formatter**: Black
- **Import sorting**: isort
- **Type hints**: Required for all function signatures
- **Docstrings**: Google style

Example:
```python
from typing import Optional, List
from datetime import datetime

from sqlalchemy.orm import Session

from src.models.compliance import Obligation


def get_obligations(
    db: Session,
    status: Optional[str] = None,
    limit: int = 100,
) -> List[Obligation]:
    """Get obligations with optional filtering.

    Args:
        db: Database session
        status: Filter by status (optional)
        limit: Maximum number of results

    Returns:
        List of obligations matching criteria

    Raises:
        ValueError: If limit is negative
    """
    if limit < 0:
        raise ValueError("Limit must be non-negative")

    query = db.query(Obligation)
    if status:
        query = query.filter(Obligation.status == status)

    return query.limit(limit).all()
```

### TypeScript/React (Frontend)

- **Linter**: ESLint with our config
- **Formatter**: Prettier
- **Type checking**: Strict TypeScript

Example:
```typescript
interface GapAnalysisProps {
  tenantId: string;
  onGapSelect?: (gap: Gap) => void;
}

export const GapAnalysisDashboard: React.FC<GapAnalysisProps> = ({
  tenantId,
  onGapSelect,
}) => {
  const [gaps, setGaps] = useState<Gap[]>([]);

  useEffect(() => {
    loadGaps();
  }, [tenantId]);

  const loadGaps = async (): Promise<void> => {
    const data = await getGaps(tenantId);
    setGaps(data);
  };

  return (
    <div className="gap-analysis">
      {/* Component JSX */}
    </div>
  );
};
```

### Pre-commit Hooks

Install pre-commit hooks:
```bash
pre-commit install
```

Run on all files:
```bash
pre-commit run --all-files
```

## Testing

### Test Structure

```
tests/
├── unit/              # Unit tests (no external dependencies)
├── integration/       # Integration tests (with DB, Redis, etc.)
├── e2e/              # End-to-end tests
└── fixtures/         # Test data and utilities
```

### Writing Tests

```python
# tests/unit/test_gap_analysis.py
import pytest
from unittest.mock import Mock, patch

from src.services.gap_analyzer import GapAnalyzer


class TestGapAnalyzer:
    """Test cases for GapAnalyzer service."""

    def test_calculate_severity_critical(self):
        """Should return CRITICAL for high-risk + near deadline."""
        analyzer = GapAnalyzer()

        severity = analyzer.calculate_severity(
            risk_score=0.9,
            days_to_deadline=5,
        )

        assert severity == GapSeverity.CRITICAL

    @patch("src.services.gap_analyzer.get_db")
    def test_analyze_coverage_with_no_gaps(self, mock_get_db):
        """Should return 100% coverage when all obligations mapped."""
        mock_db = Mock()
        mock_db.query.return_value.all.return_value = []
        mock_get_db.return_value = mock_db

        analyzer = GapAnalyzer()
        result = analyzer.analyze_coverage(tenant_id="test")

        assert result.coverage_percentage == 100.0
```

### Running Tests

```bash
# All tests
make test

# Specific test file
pytest tests/unit/test_gap_analysis.py -v

# With coverage
make test-coverage

# Integration tests only
pytest tests/integration/ -v --integration
```

### Test Coverage Requirements

- **Minimum coverage**: 80%
- **Critical paths**: 95%
- **New code**: Must have tests

## Documentation

### Code Documentation

- All public functions must have docstrings
- Complex algorithms need inline comments
- Update README if adding new features

### API Documentation

API endpoints are automatically documented via OpenAPI/Swagger:

```python
@router.get(
    "/gaps",
    response_model=GapsResponse,
    summary="List compliance gaps",
    description="Returns a paginated list of compliance gaps with filtering options.",
    tags=["gap-analysis"],
)
def list_gaps(
    severity: Optional[str] = Query(None, description="Filter by severity level"),
    limit: int = Query(100, ge=1, le=1000),
):
    """List compliance gaps.

    This endpoint returns all identified compliance gaps between
    regulatory obligations and implemented policies.
    """
    pass
```

### Architecture Documentation

For significant architectural changes, create an ADR:

```bash
# Create new ADR
cp docs/adr/template.md docs/adr/0012-your-decision.md
```

## Commit Message Guidelines

We follow [Conventional Commits](https://www.conventionalcommits.org/):

### Format

```
<type>(<scope>): <subject>

<body>

<footer>
```

### Types

- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation only
- `style`: Code style (formatting, missing semi colons, etc)
- `refactor`: Code refactoring
- `perf`: Performance improvement
- `test`: Adding tests
- `chore`: Build process or auxiliary tool changes

### Examples

```
feat(gap-analysis): add trend analysis endpoint

Implements trend calculation showing coverage changes over time.
Supports 30, 60, and 90 day time periods.

Closes #123
```

```
fix(api): resolve race condition in alert processing

The alert processing endpoint was not properly handling concurrent
requests, leading to duplicate alerts. Added proper locking.

Fixes #456
```

## Pull Request Process

### Before Submitting

1. **Verify your changes**
   ```bash
   make verify
   ```

2. **Update documentation**
   - API docs (if endpoints changed)
   - README (if user-facing changes)
   - CHANGELOG (if applicable)

3. **Write a clear description**
   - What changed and why
   - How to test
   - Screenshots (if UI changes)

### PR Review Process

1. **Automated checks** must pass:
   - CI build
   - Tests
   - Linting
   - Security scan

2. **Code review** by at least 2 maintainers

3. **Approval** required before merge

### After Merge

- Delete your feature branch
- Monitor production for issues

## Release Process

### Versioning

We follow [Semantic Versioning](https://semver.org/):

- `MAJOR`: Breaking changes
- `MINOR`: New features (backward compatible)
- `PATCH`: Bug fixes

### Creating a Release

1. Update `CHANGELOG.md`
2. Create release PR
3. After merge, tag the release:
   ```bash
   git tag -a v1.2.0 -m "Release version 1.2.0"
   git push origin v1.2.0
   ```
4. GitHub Actions will build and deploy

## Questions?

- 📖 [Documentation](https://docs.yufeed.io)
- 💬 [Discord](https://discord.gg/yufeed)
- 📧 [Email](mailto:contributors@yufeed.io)

Thank you for contributing! 🚀
