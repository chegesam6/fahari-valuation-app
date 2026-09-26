target_net_profit=is_result['net_profit']
    )
    display_cca(COMPANY, cca_result, ASKING_PRICE)
    # ── PDF REPORT GENERATION ──
    pdf_filename = "Fahari_Packaging_Valuation_Report.pdf"
    generate_pdf_report(
        company_name=COMPANY,
        analyst=ANALYST,
        dcf_result=dcf_result,
        lbo_result=lbo_result,
        sensitivity_matrix=sens_matrix,
        wacc_range=wacc_range,
        g_range=g_range,
        cca_result=cca_result,
        is_result=is_result,
        asking_price=ASKING_PRICE,
        filename=pdf_filename
    )

if __name__ == "__main__":
    run_fahari_analysis()