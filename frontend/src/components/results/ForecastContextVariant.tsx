interface Props {
  methodologyHref: string;
}

export default function ForecastContextVariant({ methodologyHref }: Props) {
  return (
    <div className="shrink-0 text-xs text-stone-500 sm:max-w-[200px] sm:text-right">
      <p>Your forecast is an estimate based on your answers.</p>
      <a
        href={methodologyHref}
        target="_blank"
        rel="noopener noreferrer"
        className="mt-1 inline-block font-semibold text-stone-600 hover:text-stone-800"
      >
        Methodology & Data Sources
      </a>
    </div>
  );
}
