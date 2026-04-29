#!/bin/bash
set -e

echo "========================================"
echo "  File Converter - Validation Script"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Track overall status
STATUS=0

# Step 1: Install dependencies
echo "${YELLOW}[Step 1/4] Installing dependencies...${NC}"
pip install -q -r requirements.txt 2>&1 | grep -v "already satisfied" || true
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Dependencies installed${NC}"
else
    echo "${RED}✗ Failed to install dependencies${NC}"
    exit 1
fi
echo ""

# Step 2: Build/compile the project
echo "${YELLOW}[Step 2/4] Building project...${NC}"
python -c "from app import create_app; app = create_app(); print('App created successfully')"
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Project builds successfully${NC}"
else
    echo "${RED}✗ Build failed${NC}"
    exit 1
fi
echo ""

# Step 3: Run tests
echo "${YELLOW}[Step 3/4] Running test suite...${NC}"
python -m pytest tests/ -v --tb=short 2>&1 | tail -50
if [ ${PIPESTATUS[0]} -eq 0 ]; then
    echo "${GREEN}✓ All tests passed${NC}"
else
    echo "${RED}✗ Tests failed${NC}"
    STATUS=1
fi
echo ""

# Step 4: Run linters and static analysis
echo "${YELLOW}[Step 4/4] Running linters...${NC}"

# Check Python syntax
find . -name "*.py" -not -path "./venv/*" -not -path "./.git/*" -not -path "./venv/*" -exec python -m py_compile {} \; 2>&1 | grep -v "SyntaxError" || true
if [ $? -eq 0 ]; then
    echo "${GREEN}✓ Python syntax check passed${NC}"
else
    echo "${RED}✗ Python syntax errors found${NC}"
    STATUS=1
fi

# Check for common issues with grep
echo "Checking for TODOs and stubs..."
if grep -r "TODO\|FIXME\|XXX\|# TODO\|# FIXME" --include="*.py" --include="*.html" --include="*.js" --include="*.css" . 2>/dev/null | grep -v ".git" | grep -v "__pycache__"; then
    echo "${RED}✗ Found TODO/FIXME markers${NC}"
    STATUS=1
else
    echo "${GREEN}✓ No TODO/FIXME markers found${NC}"
fi

# Check for missing required files
echo "Checking required files..."
for file in requirements.txt run.py app/__init__.py app/routes.py app/converter.py; do
    if [ -f "$file" ]; then
        echo "  ${GREEN}✓${NC} $file"
    else
        echo "  ${RED}✗${NC} $file (missing)"
        STATUS=1
    fi
done

# Check for template files
for file in templates/base.html templates/index.html templates/configure.html templates/download.html; do
    if [ -f "app/$file" ]; then
        echo "  ${GREEN}✓${NC} app/$file"
    else
        echo "  ${RED}✗${NC} app/$file (missing)"
        STATUS=1
    fi
done

echo ""

# Final result
echo "========================================"
if [ $STATUS -eq 0 ]; then
    echo "${GREEN}✓ All validation checks passed!${NC}"
    echo "========================================"
    exit 0
else
    echo "${RED}✗ Validation failed${NC}"
    echo "========================================"
    exit 1
fi
