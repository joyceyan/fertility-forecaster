export default function Footer() {
  return (
    <footer className="mt-12 border-t border-stone-200 pt-8 pb-12">
      <p className="text-xs leading-relaxed text-stone-500">
        <strong>Disclaimer:</strong> Fertility Forecaster provides statistical
        estimates of your odds of getting pregnant based on published medical
        research and Monte Carlo simulation. It is not medical advice.
        Individual outcomes depend on factors like ovarian reserve, sperm
        quality, and conditions not captured here. Consult a reproductive
        endocrinologist for personalized fertility guidance.
      </p>

      <div className="mt-4">
        <a
          href="/methodology.html"
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1 text-xs font-semibold text-stone-600 hover:text-stone-800"
        >
          Methodology & Data Sources
          <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
            <path strokeLinecap="round" strokeLinejoin="round" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14" />
          </svg>
        </a>
      </div>
    </footer>
  );
}
