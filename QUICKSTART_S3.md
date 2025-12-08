# Quick Start: Loading S3 Data

## ✅ Completed Steps

1. **Environment activated** - Using Conda base environment (Python 3.12.7)
2. **Dependencies installed** - boto3 (1.39.8) and pyarrow (21.0.0)
3. **Code ready** - Data retrieval module and scripts created

## 🔐 Configure AWS Credentials (Required)

Choose ONE method:

### Method 1: Using .env file (Recommended for this project)

```powershell
# 1. Copy the example file
Copy-Item .env.example .env

# 2. Edit .env and add your credentials
notepad .env
```

Add your actual credentials:
```
AWS_ACCESS_KEY_ID=AKIAIOSFODNN7EXAMPLE
AWS_SECRET_ACCESS_KEY=wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY
AWS_DEFAULT_REGION=us-east-1
```

### Method 2: AWS CLI (System-wide)

```powershell
# Install AWS CLI from: https://aws.amazon.com/cli/
aws configure
```

### Method 3: Environment Variables (Current session only)

```powershell
$env:AWS_ACCESS_KEY_ID="your_access_key"
$env:AWS_SECRET_ACCESS_KEY="your_secret_key"
$env:AWS_DEFAULT_REGION="us-east-1"
```

## 🧪 Test Your Setup

Run the test script to verify everything works:

```powershell
python scripts/test_s3_setup.py
```

This will check:
- Dependencies installed ✓
- AWS credentials configured
- S3 bucket accessible
- Data can be loaded

## 📊 Load Data

### Quick Start - Load one month:

```powershell
python scripts/load_s3_data.py --year 2020 --month 1
```

Output: `data/2020-01.csv`

### Load a date range:

```powershell
# Q1 2020
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 3

# Full year 2020
python scripts/load_s3_data.py --start-year 2020 --start-month 1 --end-year 2020 --end-month 12
```

### Custom output:

```powershell
python scripts/load_s3_data.py --year 2020 --month 1 --output data/raw/jan2020.csv
```

## 🐍 Use in Python Code

```python
from src.data_retrieval import load_month, load_date_range

# Load one month
df = load_month(2020, 1)
print(f"Loaded {len(df):,} rows")

# Load date range
df = load_date_range(2020, 1, 2020, 12)

# Filter for specific symbols
symbols = ['AAPL', 'GOOGL', 'MSFT']
df_filtered = df[df['symbol'].isin(symbols)]

# Save
df_filtered.to_csv('data/processed/filtered.csv', index=False)
```

## 📁 Files Created

- `src/data_retrieval.py` - Core module with 4 functions
- `scripts/load_s3_data.py` - Command-line interface
- `scripts/test_s3_setup.py` - Setup verification script
- `.env.example` - Credentials template
- `docs/S3_DATA_RETRIEVAL.md` - Comprehensive documentation

## 🔒 Security Notes

- `.env` is in `.gitignore` (won't be committed)
- Never commit AWS credentials to git
- Use IAM users with minimal permissions
- Consider using AWS IAM roles if running on EC2

## ❓ Troubleshooting

**"No AWS credentials found"**
→ Configure credentials using one of the 3 methods above

**"Access denied"**
→ Verify your IAM user has read access to `data-retrieval-output` bucket

**"No such bucket"**
→ Check bucket name and region

**Import errors**
→ Make sure you're in the correct environment: `conda activate base`

## 📚 Full Documentation

See `docs/S3_DATA_RETRIEVAL.md` for complete documentation including:
- Data structure details
- All function signatures
- Error handling
- Performance tips
- Integration examples
