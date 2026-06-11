export interface PnlBreakdown {
  mrp: number;
  meesho_price: number;
  commission_pct: number;
  commission_amt: number;
  gst_pct: number;
  gst_amt: number;
  seller_payout: number;
  net_margin: number;
  net_margin_pct: number;
}

export interface PriceCalcRequest {
  mrp: number;
  target_margin: number;
}
