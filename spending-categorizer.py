import pandas as pd
import os
import glob
import argparse


# ====== CATEGORY MAPPING ======
CATEGORY_MAP = {
    "Dining": "Dining",
    "Grocery": "Grocery",
    "Gas/Automotive": "Transportation",
    "Other Travel": "Travel",
    "Merchandise": "Merchandise",
    "Utilities": "Utilities",
    "Entertainment": "Entertainment",
	"Payment/Credit": None,  # Exclude payments/credits
	"Other Services": "Not Categorized",
	"Supermarkets": "Grocery",
	"Payments and Credits": None,  # Exclude payments/credits
}

def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Merge credit card CSV files and map categories."
    )

    parser.add_argument("--input", required=True,
                        help="Path to folder containing credit card CSV files")

    parser.add_argument("--output", required=True,
                        help="Path to output merged CSV file")

    return parser.parse_args()


def find_column(columns, keywords):
    for col in columns:
        for keyword in keywords:
            if keyword in col.lower():
                return col
    return None


def compute_amount(df):
    """
    Handles:
    - Single amount column
    - Separate debit / credit columns

    Debit = positive (spending)
    Credit = negative (refund/payment)
    """

    amount_col = find_column(df.columns, ["amount"])

    if amount_col:
        return pd.to_numeric(df[amount_col], errors="coerce")

    debit_col = find_column(df.columns, ["debit"])
    credit_col = find_column(df.columns, ["credit"])

    if debit_col or credit_col:
        debit = pd.to_numeric(df[debit_col], errors="coerce") if debit_col else 0
        credit = pd.to_numeric(df[credit_col], errors="coerce") if credit_col else 0

        return debit.fillna(0) - credit.fillna(0)

    return None


def main():
    args = parse_arguments()
    folder_path = args.input
    output_file = args.output

    if not os.path.isdir(folder_path):
        print(f"Error: {folder_path} is not a valid folder.")
        return

    all_files = glob.glob(os.path.join(folder_path, "*.csv"))

    if not all_files:
        print("No CSV files found.")
        return

    df_list = []

    for file in all_files:
        try:
            print(f"Processing: {file}")
            df = pd.read_csv(file)
            df.columns = [col.strip() for col in df.columns]

            # --- Transaction Date (not posted date) ---
            transaction_date_col = find_column(
                df.columns,
                ["transaction date"]
            )

            if not transaction_date_col:
                transaction_date_col = next(
                    (col for col in df.columns
                     if "date" in col.lower() and "post" not in col.lower()),
                    None
                )

            desc_col = find_column(df.columns, ["description", "merchant", "details"])
            category_col = find_column(df.columns, ["category"])

            amount_series = compute_amount(df)

            if not all([transaction_date_col, desc_col, category_col]) or amount_series is None:
                print(f"Skipping {file} (missing required columns)")
                continue

            temp_df = pd.DataFrame()
            temp_df["date"] = pd.to_datetime(df[transaction_date_col], errors="coerce")
            temp_df["transaction details"] = df[desc_col]
            temp_df["transaction amount"] = amount_series
            temp_df["category"] = df[category_col].map(CATEGORY_MAP)

            # Remove Gym (mapped to None)
            temp_df = temp_df[temp_df["category"].notna()]

            df_list.append(temp_df)

        except Exception as e:
            print(f"Error processing {file}: {e}")

    if not df_list:
        print("No valid data processed.")
        return

    merged_df = pd.concat(df_list, ignore_index=True)
    merged_df = merged_df.dropna(subset=["date", "transaction amount"])
    merged_df = merged_df.sort_values("date")

    merged_df.to_csv(output_file, index=False)

    print(f"\nDone! Merged file saved to: {output_file}")


if __name__ == "__main__":
    main()