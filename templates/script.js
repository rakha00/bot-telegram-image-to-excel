// Helper function to format numbers with "Rp" and dot separators
function formatRupiah(number) {
  if (number === null || number === undefined) {
    return "";
  }
  // Ensure the number is a string and handle potential non-numeric characters before parsing
  let stringValue = String(number).replace(/[^\d,\.-]/g, ""); // Remove non-numeric except dot, comma, minus
  stringValue = stringValue.replace(/\./g, ""); // Remove existing dots (thousand separators)
  stringValue = stringValue.replace(/,/g, "."); // Replace comma with dot for decimal parsing

  let num = parseFloat(stringValue);

  if (isNaN(num)) {
    return String(number); // Return original if not a valid number
  }

  let parts = num.toFixed(0).split("."); // Use toFixed(0) to ensure no decimals for this formatting
  let integerPart = parts[0];

  let rupiah = integerPart.replace(/\B(?=(\d{3})+(?!\d))/g, "."); // Add dot as thousand separator

  return `Rp ${rupiah}`;
}

document
  .getElementById("upload-form")
  .addEventListener("submit", async function (event) {
    event.preventDefault();

    const form = event.target;
    const formData = new FormData();
    const fileInput = document.getElementById("file");
    const reportTypeSelect = document.getElementById("reportType");
    const reportEndpoint = reportTypeSelect.value; // Ini akan menjadi URL endpoint baru

    if (fileInput.files.length > 0) {
      formData.append("file", fileInput.files[0]);
    }

    const loading = document.getElementById("loading");
    const errorContainer = document.getElementById("error-container");
    const downloadLink = document.getElementById("download-link");
    const extractedDataContainer = document.getElementById(
      "extracted-data-container"
    );
    const extractedDataDisplay = document.getElementById(
      "extracted-data-display"
    );

    loading.style.display = "block";
    extractedDataContainer.style.display = "none";
    errorContainer.style.display = "none";
    downloadLink.style.display = "none";
    extractedDataDisplay.innerHTML = ""; // Clear previous results

    try {
      const response = await fetch(reportEndpoint, {
        method: "POST",
        body: formData,
      });

      const result = await response.json();

      if (!response.ok) {
        throw new Error(
          result.reason ||
            result.error ||
            `Server responded with status ${response.status}`
        );
      }

      const jsonString = JSON.stringify(result, null, 2);

      // Process and display extracted data in input fields for each year
      if (result.read && result.read.length > 0) {
        const displayLabels = {
          cash_and_cash_equivalents: "Kas dan setara kas",
          interest_receivable: "Piutang bunga",
          member_loans: "Pinjaman anggota",
          loan_loss_provision: "Penyisihan pinjaman",
          loans_to_other_cooperatives: "Pinjaman koperasi lain",
          loan_loss_provision: "Penyisihan pinjaman",
          fixed_assets: "Aset tetap",
          accumulated_depreciation: "Akumulasi penyusutan",
          intangible_assets: "Aset takberwujud",
          accumulated_amortization: "Akumulasi amortisasi",
          other_assets: "Aset lain",
          total_assets: "Total aset",
          interest_payable: "Utang bunga",
          member_deposits: "Simpanan anggota",
          other_cooperative_deposits: "Simpanan koperasi lain",
          loan_payable: "Utang pinjaman",
          employee_benefit_liabilities: "Liabilitas imbalan kerja",
          other_liabilities: "Liabilitas lain",
          total_liabilities: "Total liabilitas",
          principal_savings: "Simpanan Pokok",
          mandatory_savings: "Simpanan Wajib",
          general_reserve: "Cadangan umum",
          retained_earnings: "Sisa hasil usaha",
          other_equity: "Ekuitas lain",
          total_equity: "Total ekuitas",
          total_liabilities_and_equity: "Total liabilitas dan ekuitas",
          // Laba Rugi specific labels
          member_participation_category: "PARTISIPASI ANGGOTA",
          interest_income: "Pendapatan bunga",
          member_participation: "Jumlah partisipasi anggota",
          operating_expenses_category: "BEBAN USAHA",
          allowance_expense: "Beban penyisihan",
          personnel_expense: "Beban kepegawaian",
          administrative_general_expenses: "Beban administrasi dan umum",
          depreciation_amortization_expenses: "Beban penyusutan dan amortisasi",
          business_expense: "Jumlah beban usaha",
          remaining_profit_bruto: "SISA HASIL USAHA BRUTO",
          investment_result: "Hasil investasi",
          cooperative_expense: "Beban perkoperasian",
          other_income_expense_category: "PENDAPATAN & BEBAN LAIN",
          other_income: "Pendapatan lain",
          other_expense: "Beban lain",
          remaining_profit_before_tax: "Sisa hasil usaha sebelum pajak",
          income_tax_expense: "Beban pajak penghasilan",
          remaining_profit: "SISA HASIL USAHA",
          other_comprehensive_income: "Penghasilan komprehensif lain",
          comprehensive_income: "PENGHASILAN KOMPREHENSIF",
          // Header labels if they appear in data
          liabilities_header: "LIABILITAS",
          equity_header: "EKUITAS",
        };

        result.read.forEach((financialData, index) => {
          const year =
            financialData.year || `Tahun Tidak Diketahui ${index + 1}`;
          const yearSection = document.createElement("div");
          yearSection.className = "year-section mb-4";

          const yearHeader = document.createElement("h3");
          yearHeader.textContent = `Data untuk Tahun: ${year}`;
          yearSection.appendChild(yearHeader);

          for (const key in financialData) {
            // Skip the 'year' key as it's handled by the section header
            const isCategoryHeader = [
              "member_participation_category",
              "operating_expenses_category",
              "other_income_expense_category",
              "liabilities_header",
              "equity_header",
            ].includes(key);
            // Periksa apakah key adalah objek dengan properti 'value' atau hanya nilai biasa
            const rawValue = financialData[key];
            const valueToDisplay =
              typeof rawValue === "object" &&
              rawValue !== null &&
              "value" in rawValue
                ? rawValue.value
                : rawValue;

            if (key !== "year" && valueToDisplay !== null) {
              const label =
                displayLabels[key] ||
                key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
              let formattedValue = valueToDisplay;

              const formGroup = document.createElement("div");
              formGroup.className = "mb-3 form-group-item";

              if (isCategoryHeader) {
                const headerElement = document.createElement("h5");
                headerElement.textContent = label;
                formGroup.appendChild(headerElement);
              } else {
                const labelElement = document.createElement("label");
                labelElement.htmlFor = `input-${year}-${key}`;
                labelElement.className = "form-label";
                labelElement.textContent = `${label}:`;

                const inputElement = document.createElement("input");
                inputElement.type = "text";
                inputElement.className = "form-control";
                inputElement.id = `input-${year}-${key}`;

                // Only apply Rupiah formatting if it's a number
                if (
                  !isNaN(parseFloat(valueToDisplay)) &&
                  isFinite(valueToDisplay)
                ) {
                  formattedValue = formatRupiah(valueToDisplay);
                }

                inputElement.value = formattedValue;
                inputElement.readOnly = true;

                formGroup.appendChild(labelElement);
                formGroup.appendChild(inputElement);
              }
              yearSection.appendChild(formGroup);
            }
          }
          extractedDataDisplay.appendChild(yearSection);
        });
        extractedDataContainer.style.display = "block";
      }

      // Create a blob from the JSON string and set it as the download link
      const blob = new Blob([jsonString], {
        type: "application/json",
      });
      const url = URL.createObjectURL(blob);
      const filename = `report_${new Date().toISOString()}.json`;
      downloadLink.href = url;
      downloadLink.download = filename;
      downloadLink.style.display = "block";
    } catch (error) {
      errorContainer.textContent = `An error occurred: ${error.message}`;
      errorContainer.style.display = "block";
    } finally {
      loading.style.display = "none";
    }
  });
