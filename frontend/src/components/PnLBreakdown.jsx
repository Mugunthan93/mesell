import { currency } from "../utils/formatters";

export default function PnLBreakdown({ result }) {
  if (!result) return null;
  const lines = [
    ["Selling price", result.selling_price],
    ["Cost price", result.cost_price],
    ["Shipping", result.shipping_cost],
    ["Shipping GST (18%)", result.shipping_gst],
    ["Payment processing (2%)", result.payment_processing],
    ["Return provision", result.return_provision],
    ["Packaging", result.packaging],
    ["Ad spend", result.ad_spend],
  ];
  return (
    <div className="rounded-xl bg-white p-6 shadow-sm ring-1 ring-slate-200">
      <h3 className="text-base font-semibold">P&amp;L breakdown</h3>
      <table className="mt-3 w-full text-sm">
        <tbody className="divide-y divide-slate-100">
          {lines.map(([label, value]) => (
            <tr key={label}>
              <td className="py-1.5 text-slate-600">{label}</td>
              <td className="py-1.5 text-right font-mono">{currency(value)}</td>
            </tr>
          ))}
          <tr className="border-t-2 border-slate-200">
            <td className="py-2 font-semibold">Net profit</td>
            <td
              className={`py-2 text-right font-mono text-lg font-semibold ${
                Number(result.net_profit) >= 0 ? "text-emerald-600" : "text-rose-600"
              }`}
            >
              {currency(result.net_profit)}
            </td>
          </tr>
          <tr>
            <td className="py-1 text-slate-500">Margin</td>
            <td className="py-1 text-right font-mono text-slate-700">
              {result.margin_percent}%
            </td>
          </tr>
        </tbody>
      </table>
      {result.alerts?.length > 0 && (
        <ul className="mt-4 space-y-2">
          {result.alerts.map((a) => (
            <li
              key={a.code}
              className={`rounded-md px-3 py-2 text-sm ${
                a.severity === "critical"
                  ? "bg-rose-50 text-rose-700"
                  : a.severity === "warn"
                    ? "bg-amber-50 text-amber-700"
                    : "bg-slate-50 text-slate-700"
              }`}
            >
              {a.message}
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
