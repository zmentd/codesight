# Manual Conda Setup for CodeSight

Since conda is installed at `D:\Programs\anaconda3`, here are the manual steps to set up the environment:

## Method 1: Using Full Paths (Recommended)

### Create Environment
```cmd
D:\Programs\anaconda3\Scripts\conda.exe env create -f environment.yml
```

### Activate Environment
```cmd
D:\Programs\anaconda3\Scripts\activate.bat codesight
```

### Alternative Activation
```cmd
call D:\Programs\anaconda3\Scripts\activate.bat codesight
```

## Method 2: Add Conda to PATH

Add these paths to your system PATH environment variable:
- `D:\Programs\anaconda3`
- `D:\Programs\anaconda3\Scripts`
- `D:\Programs\anaconda3\Library\bin`

Then you can use normal conda commands:
```cmd
conda env create -f environment.yml
conda activate codesight
```

## Method 3: Using Anaconda Prompt

1. Open "Anaconda Prompt" from Start Menu
2. Navigate to the workflow directory:
   ```cmd
   cd "d:\Prj\NBCU\storm\codesight\workflow"
   ```
3. Create environment:
   ```cmd
   conda env create -f environment.yml
   ```
4. Activate environment:
   ```cmd
   conda activate codesight
   ```

## Verification

After activation, verify the setup:

```cmd
# Check Python version
python --version

# Check installed packages
conda list

# Run tests
python -m pytest test/config/ test/core/ -v

# Run application
python main.py ct-hr-storm
```

## Available Scripts

- `setup-enhanced.bat` - Enhanced setup with better error handling
- `activate-codesight.bat` - Quick activation script
- `setup.bat` - Original setup script (updated with your conda path)

## Environment Details

The conda environment includes:
- Python 3.11
- Core dependencies: PyYAML, numpy, chardet, pytest
- Development tools: black, flake8, mypy, isort
- Optional: JPype1, faiss-cpu, httpx, requests

## Troubleshooting

If environment creation fails:
1. Make sure conda is up to date: `conda update conda`
2. Try creating with explicit python version: `conda create -n codesight python=3.11`
3. Then install requirements: `pip install -r requirements.txt`
