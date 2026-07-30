import { FormEvent, useEffect, useMemo, useRef, useState } from "react";

type RiskCapacity = "LOW" | "MEDIUM" | "HIGH";

type FinancialGoal = {
  goal_id: string;
  name: string;
  target_amount: number;
  horizon_months: number;
  priority: "LOW" | "MEDIUM" | "HIGH";
  flexibility: "FIXED" | "ADJUSTABLE" | "FLEXIBLE";
};

type Profile = {
  user_id: string;
  display_name: string;
  age: number;
  occupation: string;
  marital_status: "SINGLE" | "MARRIED" | "DIVORCED" | "WIDOWED";
  dependents: number;
  employment_stability: "LOW" | "MEDIUM" | "HIGH";
  monthly_income: number;
  total_assets: number;
  cash_savings: number;
  emergency_reserve: number;
  near_term_liabilities: number;
  monthly_expenses: number;
  total_debt: number;
  monthly_debt_payment: number;
  insurance_coverage: number;
  goal: string;
  horizon_months: number;
  goals: FinancialGoal[];
  risk_tolerance: RiskCapacity;
  risk_capacity: RiskCapacity;
  max_acceptable_drawdown: number;
  liquidity_need: number;
  liquidity_need_months: number;
  max_product_count: number;
  max_financial_apps: number;
  monitoring_frequency: "DAILY" | "WEEKLY" | "MONTHLY" | "QUARTERLY";
  lockup_tolerance_months: number;
  excluded_asset_classes: string[];
  customer_segments: string[];
};

type PlanningRequest = {
  profile: Profile;
  requested_mode: "RESEARCH_EDUCATION" | "LICENSED_ADVISORY";
  legal_evidence: {
    licensed_entity_verified: boolean;
    advisory_contract_verified: boolean;
    responsible_advisor_verified: boolean;
  };
  scenario_count: number;
};

type Allocation = {
  product_id?: string;
  product_name?: string;
  provider?: string;
  asset_class: string;
  amount: number;
  weight: number;
  expected_return_rate?: number;
  expected_return_amount: number;
  transaction_cost_amount: number;
  liquidity_score?: number;
  reference_price?: number | null;
  estimated_units?: number | null;
  lot_size?: number | null;
  execution_instruction?: string;
  source_reference?: string;
  data_timestamp?: string;
};

type AllocationExplanation = {
  asset_class: string;
  product_id?: string;
  product_name?: string;
  provider?: string;
  amount: number;
  weight: number;
  expected_return_rate: number;
  expected_return_amount: number;
  transaction_cost_amount: number;
  liquidity_score: number;
  portfolio_role: string;
  allocation_reason: string;
  limiting_factor: string;
  change_trigger: string;
  expected_return_and_risk: string;
  cost_and_liquidity: string;
  execution_conditions: string[];
  adverse_scenario: string;
  data_evidence: string[];
  result_sensitive_assumptions: string[];
};

type MonitoringTrigger = {
  trigger_type: string;
  trigger_condition: string;
  current_reference: string;
  action: string;
};

type WithdrawalOption = {
  option_type: string;
  title: string;
  available_amount: number;
  estimated_cost: string;
  portfolio_impact: string;
  conditions: string[];
  priority: number;
};

type DepositImplementationDetail = {
  product_id: string;
  bank: string;
  product_name: string;
  tenor_months: number | null;
  amount: number;
  weight: number;
  annual_rate: number;
  annual_interest_amount: number;
  term_interest_amount: number | null;
  maturity_amount: number | null;
  transaction_cost_amount: number;
  liquidity_score: number;
  selected_segment: string | null;
  conditions: string[];
  why_selected: string;
  source_reference: string;
  data_timestamp: string;
};

type StressTest = {
  scenario_name: string;
  estimated_change_amount: number;
  estimated_change_pct: number;
  assumptions: string;
};

type SelectionDecision = {
  product_id: string;
  product_name?: string | null;
  provider?: string | null;
  asset_class: string;
  status: "SELECTED_INTERNAL" | "ELIGIBLE_NOT_SELECTED" | "REJECTED";
  reason_codes: string[];
  reasons: string[];
  expected_return?: number | null;
  volatility?: number | null;
  liquidity_score?: number | null;
  minimum_investment?: number | null;
  lockup_period_days?: number | null;
  data_timestamp?: string | null;
};
type Scenario = {
  scenario_id: string;
  name: string;
  style: string;
  recommendation_role?: "RECOMMENDED" | "ALTERNATIVE" | null;
  objective_description: string;
  investable_capital: number;
  expected_return_amount: number;
  expected_return_rate: number;
  total_cost_amount: number;
  allocations: Allocation[];
  allocation_explanations?: AllocationExplanation[];
  allocation_granularity: "ASSET_CLASS" | "PRODUCT";
  risk_metrics: {
    annualized_volatility: number;
    var_95_amount: number;
    cvar_95_amount: number;
    sharpe_ratio: number | null;
    concentration_hhi: number;
    largest_asset_class_weight: number;
    liquidity_score: number;
    risk_ceiling: number;
    within_risk_ceiling: boolean;
    stress_tests: StressTest[];
  };
  operational_complexity_score: number;
  complexity_breakdown: {
    distinct_provider_count: number;
    distinct_product_count: number;
    fragment_product_count: number;
    distinct_maturity_count: number;
    smallest_allocation_amount: number;
    smallest_allocation_pct: number;
  };
  complexity_config_version: string;
  fragmentation_warning: boolean;
  complexity_resolve_count: number;
  complexity_return_delta_amount: number;
  complexity_return_delta_rate: number;
  selection_decisions: SelectionDecision[];
  trade_offs: string[];
  monitoring_triggers: MonitoringTrigger[];
  withdrawal_options: WithdrawalOption[];
  source_summary: string[];
  assumptions_that_change_result: string[];
  deposit_implementation: DepositImplementationDetail[];
};

type Recommendation = {
  released_output: {
    recommendation_id: string;
    legal_operating_mode: string;
    output_release_type: string;
    data_snapshot: string;
    model_version: string;
    financial_plan?: {
      investable_capital: number;
      emergency_reserve: number;
      near_term_liabilities: number;
      immediate_liquidity_bucket: number;
      medium_term_bucket: number;
      long_term_capacity: number;
    };
    scenarios: Scenario[];
    warnings: string[];
    assumptions: string[];
    selection_decisions?: SelectionDecision[];
    blocked_message?: string;
  };
  explanation: {
    reasoning: string[];
    source_reference: string[];
    warning: string[];
    confidence: number;
    generated_by: string;
  };
};

type ChatSection = { title: string; body: string };
type Message = {
  id: string;
  role: "assistant" | "user";
  text: string;
  sections?: ChatSection[];
  generatedBy?: string;
};

type ChatResponse = {
  message: string;
  proposed_profile_changes: Partial<Profile>;
  replanned_recommendation?: Recommendation;
  focused_scenario_id?: string | null;
  sections: ChatSection[];
  suggested_questions: string[];
  generated_by: string;
};

type Health = {
  status: string;
  llm_status: "connected" | "fallback";
  llm_provider: "groq" | "openai" | "deterministic";
  llm_model: string;
  environment: string;
  auth_required: boolean;
  allow_registration: boolean;
  data_status:
    | "OFFICIAL_DELAYED"
    | "MIXED_OFFICIAL_AND_RESEARCH"
    | "MIXED_DELAYED_WITH_FALLBACK"
    | "MOCK_FALLBACK";
  data_snapshot: string;
  data_sources_connected: number;
  data_sources_total: number;
  data_last_updated: string | null;
};

type DataSourceStatus = {
  source_id: string;
  display_name: string;
  category: string;
  source_url: string;
  cadence: string;
  operational_status: "CONNECTED" | "STALE_FALLBACK" | "ERROR" | "LICENSE_REQUIRED";
  observed_at: string | null;
  last_success_at: string | null;
  record_count: number;
  age_seconds: number | null;
  last_error: string | null;
};

type DataSummary = {
  mode: Health["data_status"];
  snapshot_id: string;
  connected_sources: number;
  fallback_sources: number;
  total_sources: number;
  last_refresh_at: string | null;
  sources: DataSourceStatus[];
};

type DepositComparisonRow = {
  product_id: string;
  provider: string;
  product_name: string;
  eligible: boolean;
  annual_rate: number;
  projected_interest: number;
  maturity_amount: number;
  data_timestamp: string;
  eligibility_reasons: string[];
};

type DepositComparison = {
  amount: number;
  tenor_months: number;
  customer_segment: string;
  guidance: string;
  calculation_note: string;
  comparisons: DepositComparisonRow[];
};

type AuthUser = {
  user_id: string;
  email: string;
  display_name: string;
  role: "admin" | "user";
};

type AuthToken = {
  access_token: string;
  expires_in: number;
  user: AuthUser;
};

type AdvisoryStatus = {
  user_id: string;
  licensed_entity_verified: boolean;
  advisory_contract_verified: boolean;
  responsible_advisor_verified: boolean;
  authorized: boolean;
  can_manage: boolean;
  verified_by: string | null;
  verified_at: string | null;
};

const FALLBACK_REQUEST: PlanningRequest = {
  profile: {
    user_id: "demo-user",
    display_name: "Nhà đầu tư demo",
    age: 32,
    occupation: "Chuyên viên công nghệ",
    marital_status: "MARRIED",
    dependents: 1,
    employment_stability: "HIGH",
    monthly_income: 55_000_000,
    total_assets: 650_000_000,
    cash_savings: 180_000_000,
    emergency_reserve: 90_000_000,
    near_term_liabilities: 40_000_000,
    monthly_expenses: 25_000_000,
    total_debt: 120_000_000,
    monthly_debt_payment: 8_000_000,
    insurance_coverage: 500_000_000,
    goal: "Tích lũy mua nhà và tăng trưởng tài sản trong 7 năm",
    horizon_months: 84,
    goals: [
      {
        goal_id: "home",
        name: "Tích lũy mua nhà",
        target_amount: 1_500_000_000,
        horizon_months: 84,
        priority: "HIGH",
        flexibility: "ADJUSTABLE"
      }
    ],
    risk_tolerance: "MEDIUM",
    risk_capacity: "MEDIUM",
    max_acceptable_drawdown: 0.15,
    liquidity_need: 60_000_000,
    liquidity_need_months: 6,
    max_product_count: 6,
    max_financial_apps: 3,
    monitoring_frequency: "MONTHLY",
    lockup_tolerance_months: 12,
    excluded_asset_classes: [],
    customer_segments: ["retail"]
  },
  requested_mode: "RESEARCH_EDUCATION",
  legal_evidence: {
    licensed_entity_verified: false,
    advisory_contract_verified: false,
    responsible_advisor_verified: false
  },
  scenario_count: 3
};

const ASSET_LABELS: Record<string, string> = {
  CASH: "Tiền mặt",
  GOLD: "Vàng",
  SILVER: "Bạc",
  DEPOSIT: "Tiền gửi",
  EQUITY: "Cổ phiếu",
  ETF: "ETF VN30",
  BOND_FUND: "Quỹ trái phiếu"
};

const readableProductName = (productId: string, productName?: string | null) => {
  if (productName && !/[?�]/.test(productName)) return productName;

  if (productId === "cash-vnd-internal") return "Tiền mặt / Tài khoản thanh toán VND";
  if (productId.includes("bond-fund-vcbf-fif")) return "Quỹ đầu tư trái phiếu VCBF-FIF";
  if (productId.includes("bond-fund-vnd")) return "Quỹ trái phiếu VND";
  if (productId.includes("gold-ring")) return "Vàng nhẫn tròn 9999";
  if (productId.includes("gold-sjc") || productId.includes("gold-bullion")) {
    return "Vàng miếng SJC";
  }

  const deposit = productId.match(/deposit-([a-z]+)-(?:online-)?(\d+)m/i);
  if (deposit) {
    const bankNames: Record<string, string> = {
      mbbank: "MBBank",
      techcombank: "Techcombank",
      vpbank: "VPBank",
      vietcombank: "Vietcombank"
    };
    const bank = bankNames[deposit[1].toLowerCase()] || deposit[1].toUpperCase();
    return `Tiền gửi online ${deposit[2]} tháng · ${bank}`;
  }

  const equity = productId.match(/(?:vn30-)?equity-([a-z0-9]+)-(?:vnstock|mock)/i);
  if (equity) return `Cổ phiếu ${equity[1].toUpperCase()} · HOSE`;
  const etf = productId.match(/(?:vn30-)?etf-([a-z0-9]+)-(?:vnstock|mock)/i);
  if (etf) return `ETF ${etf[1].toUpperCase()} theo dõi VN30`;

  return productId
    .replace(/-(?:delayed|mock|vnstock)$/i, "")
    .split("-")
    .map((part) => part.charAt(0).toUpperCase() + part.slice(1))
    .join(" ");
};

const COLORS: Record<string, string> = {
  CASH: "#82c4b2",
  GOLD: "#d5a847",
  SILVER: "#9aa8b1",
  DEPOSIT: "#397565",
  EQUITY: "#d96f52",
  ETF: "#c9864c",
  BOND_FUND: "#6875a6"
};

const money = new Intl.NumberFormat("vi-VN", {
  style: "currency",
  currency: "VND",
  maximumFractionDigits: 0
});

const compactMoney = (value: number) =>
  `${new Intl.NumberFormat("vi-VN", {
    notation: "compact",
    maximumFractionDigits: 1
  }).format(value)}₫`;

const pct = (value: number) =>
  new Intl.NumberFormat("vi-VN", {
    style: "percent",
    maximumFractionDigits: 2
  }).format(value);

const dateTime = (value: string | null) =>
  value
    ? new Intl.DateTimeFormat("vi-VN", {
        dateStyle: "short",
        timeStyle: "short"
      }).format(new Date(value))
    : "Chưa có dữ liệu";

const dataModeLabel = (mode?: Health["data_status"]) =>
  mode === "OFFICIAL_DELAYED"
    ? "DỮ LIỆU CHÍNH THỨC · CÓ ĐỘ TRỄ"
    : mode === "MIXED_OFFICIAL_AND_RESEARCH"
      ? "DỮ LIỆU CHÍNH THỨC + NGHIÊN CỨU"
    : mode === "MIXED_DELAYED_WITH_FALLBACK"
      ? "DỮ LIỆU HỖN HỢP · FALLBACK"
      : "DỮ LIỆU MÔ PHỎNG";

const uid = () => `${Date.now()}-${Math.random().toString(16).slice(2)}`;

async function api<T>(path: string, options?: RequestInit): Promise<T> {
  const accessToken = localStorage.getItem("monopoly_access_token");
  let response: Response;
  const baseUrl = import.meta.env.VITE_API_URL || "";
  const fullPath = path.startsWith("/") && baseUrl.endsWith("/")
    ? baseUrl.slice(0, -1) + path
    : baseUrl + path;
  try {
    response = await fetch(fullPath, {
      headers: {
        "Content-Type": "application/json",
        ...(accessToken ? { Authorization: `Bearer ${accessToken}` } : {}),
        ...(options?.headers || {})
      },
      ...options
    });
  } catch {
    throw new Error(
      navigator.onLine
        ? "Máy chủ phân tích đang tạm mất kết nối. Kết quả của bạn vẫn được giữ; vui lòng thử gửi lại sau ít giây."
        : "Thiết bị đang ngoại tuyến. Hãy kiểm tra kết nối mạng rồi gửi lại câu hỏi."
    );
  }
  if (!response.ok) {
    const body = await response.json().catch(() => ({}));
    const detail = body.detail;
    const readableDetail =
      typeof detail === "string"
        ? detail
        : Array.isArray(detail)
          ? detail
              .map((item) => {
                const path = Array.isArray(item.loc) ? item.loc.slice(1).join(" → ") : "";
                return `${path ? `${path}: ` : ""}${item.msg || "Dữ liệu chưa hợp lệ"}`;
              })
              .join(". ")
          : detail
            ? JSON.stringify(detail)
            : "Không thể kết nối hệ thống.";
    throw new Error(readableDetail);
  }
  return response.json();
}

function NumberField({
  label,
  value,
  onChange
}: {
  label: string;
  value: number;
  onChange: (value: number) => void;
}) {
  return (
    <label className="field">
      <span>{label}</span>
      <div className="money-input">
        <input
          type="number"
          min={0}
          step={1_000_000}
          placeholder="0"
          value={value === 0 ? "" : value}
          onChange={(event) => {
            const val = event.target.value;
            onChange(val === "" ? 0 : Number(val));
          }}
        />
        <em>VND</em>
      </div>
    </label>
  );
}

function App() {
  const [request, setRequest] = useState<PlanningRequest>(FALLBACK_REQUEST);
  const [recommendation, setRecommendation] = useState<Recommendation | null>(null);
  const [activeScenario, setActiveScenario] = useState(0);
  const [health, setHealth] = useState<Health | null>(null);
  const [authUser, setAuthUser] = useState<AuthUser | null>(null);
  const [authMode, setAuthMode] = useState<"login" | "register">("login");
  const [authEmail, setAuthEmail] = useState("");
  const [authPassword, setAuthPassword] = useState("");
  const [authName, setAuthName] = useState("");
  const [authLoading, setAuthLoading] = useState(false);
  const [authError, setAuthError] = useState("");
  const [loading, setLoading] = useState(false);
  const [chatLoading, setChatLoading] = useState(false);
  const [complexityLoadingId, setComplexityLoadingId] = useState<string | null>(null);
  const [error, setError] = useState("");
  const [chatInput, setChatInput] = useState("");
  const [suggestions, setSuggestions] = useState<string[]>([
    "Hãy phân tích hồ sơ mẫu",
    "Hệ thống này hoạt động thế nào?"
  ]);
  const [messages, setMessages] = useState<Message[]>([
    {
      id: uid(),
      role: "assistant",
      text:
        "Chào bạn, tôi là Monopoly AI. Tôi giúp bạn khám phá các phương án tiết kiệm và đầu tư đa tài sản bằng hội thoại.",
      sections: [
        {
          title: "Tôi có thể làm gì?",
          body:
            "Đọc mục tiêu và dòng tiền, chạy bộ tối ưu định lượng, so sánh ba phương án, giải thích rủi ro và lập lại kế hoạch khi hoàn cảnh thay đổi."
        },
        {
          title: "Ranh giới an toàn",
          body:
            "AI chỉ diễn giải dữ liệu đã qua kiểm duyệt. Mọi số tiền và tỷ trọng do rule engine cùng CP-SAT tính toán; hệ thống không đặt lệnh giao dịch."
        }
      ]
    }
  ]);
  const [audit, setAudit] = useState<Array<Record<string, unknown>>>([]);
  const [showAudit, setShowAudit] = useState(false);
  const [dataSummary, setDataSummary] = useState<DataSummary | null>(null);
  const [showDataSources, setShowDataSources] = useState(false);
  const [dataLoading, setDataLoading] = useState(false);
  const [advisoryStatus, setAdvisoryStatus] = useState<AdvisoryStatus | null>(null);
  const [advisoryDraft, setAdvisoryDraft] = useState({
    licensed_entity_verified: false,
    advisory_contract_verified: false,
    responsible_advisor_verified: false
  });
  const [showAdvisory, setShowAdvisory] = useState(false);
  const [advisorySaving, setAdvisorySaving] = useState(false);
  const [showDepositComparison, setShowDepositComparison] = useState(false);
  const [depositAmount, setDepositAmount] = useState(100_000_000);
  const [depositTenor, setDepositTenor] = useState(12);
  const [depositSegment, setDepositSegment] = useState("retail");
  const [depositResult, setDepositResult] = useState<DepositComparison | null>(null);
  const [depositLoading, setDepositLoading] = useState(false);
  const [view, setView] = useState<"chat" | "results" | "profile">("chat");
  const [activeProfileSection, setActiveProfileSection] = useState("demographics");
  const [profileSaving, setProfileSaving] = useState(false);
  const [profileSaved, setProfileSaved] = useState(false);
  const [historySessions, setHistorySessions] = useState<any[]>([]);
  const messageListRef = useRef<HTMLDivElement>(null);
  const insightPanelRef = useRef<HTMLElement>(null);

  const fetchHistorySessions = async () => {
    try {
      const token = localStorage.getItem("monopoly_access_token");
      if (token || !health?.auth_required) {
        const data = await api<any[]>("/api/v1/me/recommendations");
        setHistorySessions(data);
      }
    } catch {
      // Ignore
    }
  };

  const loadSession = async (id: string) => {
    try {
      const data = await api<any>(`/api/v1/recommendations/${id}`);
      if (data.request) {
        setRequest(data.request);
      }
      setRecommendation({
        released_output: data.released_output,
        explanation: data.explanation,
        status: data.status,
      } as Recommendation);
      setView("results");
    } catch (e) {
      setError("Không thể tải phiên làm việc này.");
    }
  };

  useEffect(() => {
    const bootstrap = async () => {
      try {
        const status = await api<Health>("/health");
        let currentAdvisoryStatus: AdvisoryStatus | null = null;
        setHealth(status);
        if (status.auth_required && localStorage.getItem("monopoly_access_token")) {
          try {
            const currentUser = await api<AuthUser>("/api/v1/auth/me");
            currentAdvisoryStatus = await api<AdvisoryStatus>(
              "/api/v1/advisory/status"
            );
            setAuthUser(currentUser);
            setAdvisoryStatus(currentAdvisoryStatus);
            setAdvisoryDraft({
              licensed_entity_verified:
                currentAdvisoryStatus.licensed_entity_verified,
              advisory_contract_verified:
                currentAdvisoryStatus.advisory_contract_verified,
              responsible_advisor_verified:
                currentAdvisoryStatus.responsible_advisor_verified
            });
          } catch {
            localStorage.removeItem("monopoly_access_token");
          }
        } else if (!status.auth_required) {
          const currentUser: AuthUser = {
            user_id: "demo-user",
            email: "demo@local.invalid",
            display_name: "Nhà đầu tư demo",
            role: "admin"
          };
          currentAdvisoryStatus = await api<AdvisoryStatus>(
            "/api/v1/advisory/status"
          );
          setAuthUser(currentUser);
          setAdvisoryStatus(currentAdvisoryStatus);
          setAdvisoryDraft({
            licensed_entity_verified:
              currentAdvisoryStatus.licensed_entity_verified,
            advisory_contract_verified:
              currentAdvisoryStatus.advisory_contract_verified,
            responsible_advisor_verified:
              currentAdvisoryStatus.responsible_advisor_verified
          });
        }
        const defaultRequest = await api<PlanningRequest>(
          "/api/v1/demo/default-request"
        );
        setRequest(
          currentAdvisoryStatus
            ? {
                ...defaultRequest,
                requested_mode: currentAdvisoryStatus.authorized
                  ? "LICENSED_ADVISORY"
                  : "RESEARCH_EDUCATION",
                legal_evidence: {
                  licensed_entity_verified:
                    currentAdvisoryStatus.licensed_entity_verified,
                  advisory_contract_verified:
                    currentAdvisoryStatus.advisory_contract_verified,
                  responsible_advisor_verified:
                    currentAdvisoryStatus.responsible_advisor_verified
                }
              }
            : defaultRequest
        );
      } catch {
        setRequest(FALLBACK_REQUEST);
      }
    };
    bootstrap();
  }, []);

  useEffect(() => {
    const messageList = messageListRef.current;
    if (messageList) {
      messageList.scrollTo({
        top: messageList.scrollHeight,
        behavior: "smooth"
      });
    }
  }, [messages, chatLoading]);

  useEffect(() => {
    insightPanelRef.current?.scrollTo({ top: 0, behavior: "smooth" });
  }, [recommendation?.released_output.recommendation_id, activeScenario]);

  useEffect(() => {
    const fetchHistory = async () => {
      const recId = recommendation?.released_output.recommendation_id;
      if (recId) {
        try {
          const res = await api<{messages: {role: string, content: string}[]}>(
            `/api/v1/recommendations/${recId}/chat`
          );
          if (res.messages && res.messages.length > 0) {
            setMessages(res.messages.map(m => ({
              id: uid(),
              role: m.role as "user" | "assistant",
              text: m.content
            })));
          }
        } catch {
          // fallback to current messages
        }
      }
    };
    fetchHistory();
  }, [recommendation?.released_output.recommendation_id]);

  useEffect(() => {
    if (view === "chat" || view === "results") {
      fetchHistorySessions();
    }
  }, [view, health?.auth_required]);

  const profile = request.profile;
  const capital =
    profile.total_assets - profile.emergency_reserve - profile.near_term_liabilities;
  const scenarios = recommendation?.released_output.scenarios || [];
  const scenario = scenarios[activeScenario];

  const scenarioInsights = useMemo(() => {
    if (!scenario) return [];
    const largest = [...scenario.allocations].sort((a, b) => b.amount - a.amount)[0];
    const stress = [...scenario.risk_metrics.stress_tests].sort(
      (a, b) => a.estimated_change_amount - b.estimated_change_amount
    )[0];
    return [
      {
        label: "Vai trò",
        text: scenario.objective_description
      },
      {
        label: "Điểm nhấn",
        text: largest
          ? `${ASSET_LABELS[largest.asset_class] || largest.asset_class} là nhóm lớn nhất ở ${pct(largest.weight)}.`
          : "Không có phân bổ được phát hành."
      },
      {
        label: "Rủi ro cần nhớ",
        text: stress
          ? `${stress.scenario_name}: ${money.format(stress.estimated_change_amount)} theo giả định stress.`
          : `VaR 95% ở mức ${money.format(scenario.risk_metrics.var_95_amount)}.`
      },
      {
        label: "Đánh đổi",
        text: scenario.trade_offs[0] || "Không có đánh đổi bổ sung."
      }
    ];
  }, [scenario]);

  const updateProfile = <K extends keyof Profile>(key: K, value: Profile[K]) => {
    setProfileSaved(false);
    setRequest((current) => ({
      ...current,
      profile: { ...current.profile, [key]: value }
    }));
  };

  const runPlan = async (event?: FormEvent) => {
    event?.preventDefault();
    setLoading(true);
    setError("");
    setMessages((current) => [
      ...current,
      {
        id: uid(),
        role: "user",
        text: recommendation
          ? "Hãy chạy lại toàn bộ phân tích với hồ sơ vừa cập nhật."
          : "Hãy phân tích hồ sơ tài chính này và cho tôi các phương án có thể so sánh."
      }
    ]);
    try {
      const result = await api<Recommendation>("/api/v1/recommendations", {
        method: "POST",
        body: JSON.stringify(request)
      });
      setRecommendation(result);
      setActiveScenario(0);
      setView("results");
      setSuggestions([
        "So sánh cả 3 phương án",
        "Rủi ro lớn nhất là gì?",
        "Giải thích phân bổ tài sản",
        "Nếu tôi nạp thêm 50 triệu thì sao?"
      ]);
      setMessages((current) => [
        ...current,
        {
          id: uid(),
          role: "assistant",
          text:
            result.released_output.output_release_type === "BLOCKED"
              ? result.released_output.blocked_message || "Kết quả bị chặn bởi Compliance Gate."
              : result.released_output.output_release_type === "ADVISORY_SELECTED"
                ? `Tôi đã hoàn tất pipeline 13 bước và phát hành ${result.released_output.scenarios.length} phương án Advisor. Phương án đầu tiên là khuyến nghị; hai phương án còn lại là lựa chọn thay thế để so sánh.`
                : `Tôi đã hoàn tất pipeline 13 bước và tạo ${result.released_output.scenarios.length} phương án. Hãy chọn một phương án ở bảng bên phải hoặc hỏi tôi trực tiếp.`,
          sections:
            result.released_output.output_release_type === "BLOCKED"
              ? result.released_output.warnings.map((warning) => ({
                  title: "Cảnh báo kiểm duyệt",
                  body: warning
                }))
              : [
                  {
                    title: "Điểm bắt đầu nên xem",
                    body:
                      result.explanation.reasoning[0] ||
                      "Ba phương án biểu diễn ba mức đánh đổi khác nhau."
                  },
                  {
                    title: "Nguồn số liệu",
                    body: `${result.released_output.data_snapshot} · ${result.released_output.model_version}`
                  }
                ],
          generatedBy: result.explanation.generated_by
        }
      ]);
    } catch (cause) {
      const message = cause instanceof Error ? cause.message : "Có lỗi khi tối ưu.";
      setError(message);
      setMessages((current) => [
        ...current,
        { id: uid(), role: "assistant", text: message }
      ]);
    } finally {
      setLoading(false);
    }
  };

  const ask = async (text: string) => {
    if (!text.trim()) return;
    const normalizedText = text.toLocaleLowerCase("vi-VN");
    if (
      !recommendation &&
      normalizedText.includes("phân tích hồ sơ")
    ) {
      await runPlan();
      return;
    }

    setMessages((current) => [...current, { id: uid(), role: "user", text }]);
    setChatLoading(true);
    try {
      const result = await api<ChatResponse>("/api/v1/chat", {
        method: "POST",
        body: JSON.stringify({
          recommendation_id: recommendation?.released_output.recommendation_id || null,
          active_scenario_id: scenario?.scenario_id,
          message: text,
          conversation_history: messages.slice(-8).map((item) => ({
            role: item.role,
            content: item.text
          }))
        })
      });
      setMessages((current) => [
        ...current,
        {
          id: uid(),
          role: "assistant",
          text: result.message,
          sections: result.sections,
          generatedBy: result.generated_by
        }
      ]);
      setSuggestions(result.suggested_questions || []);
      if (result.focused_scenario_id && recommendation) {
        const focusedIndex = recommendation.released_output.scenarios.findIndex(
          (item) => item.scenario_id === result.focused_scenario_id
        );
        if (focusedIndex >= 0) setActiveScenario(focusedIndex);
      }
      if (result.replanned_recommendation) {
        setRecommendation(result.replanned_recommendation);
        setActiveScenario(0);
        setRequest((current) => ({
          ...current,
          profile: { ...current.profile, ...result.proposed_profile_changes }
        }));
      }
    } catch (cause) {
      setMessages((current) => [
        ...current,
        {
          id: uid(),
          role: "assistant",
          text: cause instanceof Error ? cause.message : "Không xử lý được câu hỏi."
        }
      ]);
    } finally {
      setChatLoading(false);
    }
  };

  const sendChat = async (event: FormEvent) => {
    event.preventDefault();
    const text = chatInput.trim();
    if (!text || chatLoading) return;
    setChatInput("");
    await ask(text);
  };

  const loadAudit = async () => {
    if (!recommendation) return;
    const rows = await api<Array<Record<string, unknown>>>(
      `/api/v1/recommendations/${recommendation.released_output.recommendation_id}/audit`
    );
    setAudit(rows);
    setShowAudit(true);
  };

  const loadDataSources = async () => {
    setDataLoading(true);
    setError("");
    try {
      const summary = await api<DataSummary>("/api/v1/data-sources");
      setDataSummary(summary);
      setShowDataSources(true);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không tải được trạng thái dữ liệu.");
    } finally {
      setDataLoading(false);
    }
  };

  const refreshDataSources = async () => {
    setDataLoading(true);
    try {
      const summary = await api<DataSummary>("/api/v1/admin/data-sources/refresh", {
        method: "POST"
      });
      setDataSummary(summary);
      const status = await api<Health>("/health");
      setHealth(status);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể đồng bộ dữ liệu.");
    } finally {
      setDataLoading(false);
    }
  };

  const compareDepositRates = async (event?: FormEvent) => {
    event?.preventDefault();
    setDepositLoading(true);
    setError("");
    try {
      const query = new URLSearchParams({
        amount: String(depositAmount),
        tenor_months: String(depositTenor),
        customer_segment: depositSegment
      });
      const result = await api<DepositComparison>(
        `/api/v1/deposits/compare?${query.toString()}`
      );
      setDepositResult(result);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể so sánh lãi suất.");
    } finally {
      setDepositLoading(false);
    }
  };

  const openDepositComparison = () => {
    setDepositAmount(
      Math.max(1_000_000, Math.min(Math.max(capital, 100_000_000), 3_000_000_000))
    );
    setDepositSegment(profile.customer_segments[0] || "retail");
    setDepositResult(null);
    setShowDepositComparison(true);
  };

  const submitAuth = async (event: FormEvent) => {
    event.preventDefault();
    setAuthLoading(true);
    setAuthError("");
    try {
      const result = await api<AuthToken>(
        authMode === "login" ? "/api/v1/auth/login" : "/api/v1/auth/register",
        {
          method: "POST",
          body: JSON.stringify(
            authMode === "login"
              ? { email: authEmail, password: authPassword }
              : { email: authEmail, password: authPassword, display_name: authName }
          )
        }
      );
      localStorage.setItem("monopoly_access_token", result.access_token);
      setAuthUser(result.user);
      const [defaultRequest, currentAdvisoryStatus] = await Promise.all([
        api<PlanningRequest>("/api/v1/demo/default-request"),
        api<AdvisoryStatus>("/api/v1/advisory/status")
      ]);
      setAdvisoryStatus(currentAdvisoryStatus);
      setAdvisoryDraft({
        licensed_entity_verified: currentAdvisoryStatus.licensed_entity_verified,
        advisory_contract_verified: currentAdvisoryStatus.advisory_contract_verified,
        responsible_advisor_verified:
          currentAdvisoryStatus.responsible_advisor_verified
      });
      setRequest({
        ...defaultRequest,
        requested_mode: currentAdvisoryStatus.authorized
          ? "LICENSED_ADVISORY"
          : "RESEARCH_EDUCATION",
        legal_evidence: {
          licensed_entity_verified:
            currentAdvisoryStatus.licensed_entity_verified,
          advisory_contract_verified:
            currentAdvisoryStatus.advisory_contract_verified,
          responsible_advisor_verified:
            currentAdvisoryStatus.responsible_advisor_verified
        }
      });
      setAuthPassword("");
    } catch (cause) {
      setAuthError(cause instanceof Error ? cause.message : "Không thể xác thực.");
    } finally {
      setAuthLoading(false);
    }
  };

  const logout = () => {
    localStorage.removeItem("monopoly_access_token");
    setAuthUser(null);
    setAdvisoryStatus(null);
    setShowAdvisory(false);
    setRecommendation(null);
    setRequest((current) => ({
      ...current,
      requested_mode: "RESEARCH_EDUCATION",
      legal_evidence: {
        licensed_entity_verified: false,
        advisory_contract_verified: false,
        responsible_advisor_verified: false
      }
    }));
  };

  const openAdvisory = () => {
    if (advisoryStatus) {
      setAdvisoryDraft({
        licensed_entity_verified: advisoryStatus.licensed_entity_verified,
        advisory_contract_verified: advisoryStatus.advisory_contract_verified,
        responsible_advisor_verified:
          advisoryStatus.responsible_advisor_verified
      });
    }
    setShowAdvisory(true);
  };

  const useResearchMode = () => {
    setRequest((current) => ({
      ...current,
      requested_mode: "RESEARCH_EDUCATION",
      legal_evidence: {
        licensed_entity_verified: false,
        advisory_contract_verified: false,
        responsible_advisor_verified: false
      }
    }));
    setShowAdvisory(false);
  };

  const useAdvisoryMode = () => {
    if (!advisoryStatus?.authorized) {
      setError(
        "Chế độ Advisor chỉ có thể được chọn sau khi đủ ba điều kiện pháp lý."
      );
      return;
    }
    setRequest((current) => ({
      ...current,
      requested_mode: "LICENSED_ADVISORY",
      legal_evidence: {
        licensed_entity_verified: advisoryStatus.licensed_entity_verified,
        advisory_contract_verified: advisoryStatus.advisory_contract_verified,
        responsible_advisor_verified:
          advisoryStatus.responsible_advisor_verified
      }
    }));
    setShowAdvisory(false);
  };

  const saveAdvisoryStatus = async () => {
    setAdvisorySaving(true);
    setError("");
    try {
      const status = await api<AdvisoryStatus>("/api/v1/admin/advisory/status", {
        method: "PUT",
        body: JSON.stringify(advisoryDraft)
      });
      setAdvisoryStatus(status);
      setRequest((current) => ({
        ...current,
        requested_mode: status.authorized
          ? "LICENSED_ADVISORY"
          : "RESEARCH_EDUCATION",
        legal_evidence: {
          licensed_entity_verified: status.licensed_entity_verified,
          advisory_contract_verified: status.advisory_contract_verified,
          responsible_advisor_verified: status.responsible_advisor_verified
        }
      }));
      if (status.authorized) setShowAdvisory(false);
    } catch (cause) {
      setError(
        cause instanceof Error
          ? cause.message
          : "Không thể cập nhật quyền Advisor."
      );
    } finally {
      setAdvisorySaving(false);
    }
  };

  const consolidateActiveScenario = async () => {
    if (!recommendation || !scenario || scenario.complexity_resolve_count >= 3) return;
    setComplexityLoadingId(scenario.scenario_id);
    setError("");
    try {
      const result = await api<Recommendation>(
        `/api/v1/recommendations/${recommendation.released_output.recommendation_id}/scenarios/${scenario.scenario_id}/consolidate`,
        { method: "POST" }
      );
      setRecommendation(result);
      const updatedIndex = result.released_output.scenarios.findIndex(
        (item) => item.scenario_id === scenario.scenario_id
      );
      if (updatedIndex >= 0) setActiveScenario(updatedIndex);
      const updated = result.released_output.scenarios[updatedIndex >= 0 ? updatedIndex : activeScenario];
      setMessages((current) => [
        ...current,
        {
          id: uid(),
          role: "assistant",
          text: updated
            ? `Đã re-solve riêng phương án ${updated.name}: độ phức tạp ${updated.operational_complexity_score.toFixed(1)}/100, thay đổi lợi nhuận kỳ vọng ${money.format(updated.complexity_return_delta_amount)}/năm. Các phương án khác được giữ nguyên.`
            : "Đã hoàn tất re-solve giảm phân mảnh cho phương án đang xem.",
          generatedBy: result.explanation.generated_by
        }
      ]);
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể gộp phương án.");
    } finally {
      setComplexityLoadingId(null);
    }
  };
  const downloadReport = async () => {
    if (!recommendation) return;
    const token = localStorage.getItem("monopoly_access_token");
    const baseUrl = import.meta.env.VITE_API_URL || "";
    const response = await fetch(
      `${baseUrl}/api/v1/recommendations/${recommendation.released_output.recommendation_id}/report.pdf`,
      { headers: token ? { Authorization: `Bearer ${token}` } : {} }
    );
    if (!response.ok) {
      setError("Không thể tải báo cáo PDF.");
      return;
    }
    const url = URL.createObjectURL(await response.blob());
    const link = document.createElement("a");
    link.href = url;
    link.download = `portfolio-report-${recommendation.released_output.recommendation_id}.pdf`;
    link.click();
    URL.revokeObjectURL(url);
  };

  const updateGoal = <K extends keyof FinancialGoal>(
    index: number,
    key: K,
    value: FinancialGoal[K]
  ) => {
    setProfileSaved(false);
    setRequest((current) => {
      const goals = current.profile.goals.map((goal, goalIndex) =>
        goalIndex === index ? { ...goal, [key]: value } : goal
      );
      const primary = goals[0];
      return {
        ...current,
        profile: {
          ...current.profile,
          goals,
          ...(index === 0 && primary
            ? { goal: primary.name, horizon_months: primary.horizon_months }
            : {})
        }
      };
    });
  };

  const addGoal = () => {
    if (profile.goals.length >= 10) return;
    updateProfile("goals", [
      ...profile.goals,
      {
        goal_id: uid(),
        name: "Mục tiêu mới",
        target_amount: 100_000_000,
        horizon_months: 36,
        priority: "MEDIUM",
        flexibility: "ADJUSTABLE"
      }
    ]);
  };

  const removeGoal = (index: number) => {
    const goals = profile.goals.filter((_, goalIndex) => goalIndex !== index);
    updateProfile("goals", goals);
    if (index === 0 && goals[0]) {
      updateProfile("goal", goals[0].name);
      updateProfile("horizon_months", goals[0].horizon_months);
    }
  };

  const saveProfile = async (): Promise<boolean> => {
    setProfileSaving(true);
    setProfileSaved(false);
    setError("");
    try {
      const saved = await api<Profile>("/api/v1/me/profile", {
        method: "PUT",
        body: JSON.stringify(profile)
      });
      setRequest((current) => ({ ...current, profile: saved }));
      setProfileSaved(true);
      return true;
    } catch (cause) {
      setError(cause instanceof Error ? cause.message : "Không thể lưu hồ sơ.");
      return false;
    } finally {
      setProfileSaving(false);
    }
  };

  const saveAndAnalyze = async () => {
    if (await saveProfile()) {
      await runPlan();
    }
  };

  if (health?.auth_required && !authUser) {
    return (
      <main className="auth-shell">
        <section className="auth-card">
          <div className="brand auth-brand">
            <span className="brand-mark">M</span>
            <div>
              <strong>MONOPOLY AI</strong>
              <small>SECURE PORTFOLIO CONVERSATION</small>
            </div>
          </div>
          <span className="eyebrow">Không gian tư vấn riêng tư</span>
          <h1>{authMode === "login" ? "Đăng nhập để tiếp tục" : "Tạo tài khoản vận hành"}</h1>
          <p>Mỗi hồ sơ, cuộc trò chuyện và báo cáo được tách biệt theo tài khoản.</p>
          <form onSubmit={submitAuth}>
            {authMode === "register" && (
              <label className="field">
                <span>Tên hiển thị</span>
                <input
                  value={authName}
                  onChange={(event) => setAuthName(event.target.value)}
                  required
                  autoComplete="name"
                />
              </label>
            )}
            <label className="field">
              <span>Email</span>
              <input
                type="email"
                value={authEmail}
                onChange={(event) => setAuthEmail(event.target.value)}
                required
                autoComplete="email"
              />
            </label>
            <label className="field">
              <span>Mật khẩu</span>
              <input
                type="password"
                minLength={authMode === "register" ? 10 : 1}
                value={authPassword}
                onChange={(event) => setAuthPassword(event.target.value)}
                required
                autoComplete={authMode === "login" ? "current-password" : "new-password"}
              />
            </label>
            {authError && <p className="auth-error">{authError}</p>}
            <button className="auth-submit" disabled={authLoading}>
              {authLoading
                ? "Đang xác thực…"
                : authMode === "login"
                  ? "Đăng nhập"
                  : "Tạo tài khoản"}
            </button>
          </form>
          {health.allow_registration && (
            <button
              className="auth-switch"
              onClick={() => {
                setAuthMode((current) => (current === "login" ? "register" : "login"));
                setAuthError("");
              }}
            >
              {authMode === "login"
                ? "Chưa có tài khoản? Đăng ký"
                : "Đã có tài khoản? Đăng nhập"}
            </button>
          )}
        </section>
      </main>
    );
  }

  if (view === "profile") {
    const monthlySurplus =
      profile.monthly_income - profile.monthly_expenses - profile.monthly_debt_payment;
    const profileSections = [
      { id: "demographics", number: "01", label: "Nhân khẩu học", caption: "Bối cảnh cuộc sống" },
      { id: "financial", number: "02", label: "Tài chính", caption: "Dòng tiền & tài sản" },
      { id: "goals", number: "03", label: "Mục tiêu", caption: "Đích đến ưu tiên" },
      { id: "risk", number: "04", label: "Rủi ro", caption: "Khả năng chịu đựng" },
      { id: "convenience", number: "05", label: "Thuận tiện", caption: "Cách bạn muốn quản lý" }
    ];

    return (
      <div className="app-shell profile-workspace">
        <header className="topbar">
          <div className="brand">
            <span className="brand-mark">M</span>
            <div>
              <strong>MONOPOLY AI</strong>
              <small>FINANCIAL PROFILE CENTER</small>
            </div>
          </div>
          <nav className="workspace-nav" aria-label="Không gian làm việc">
            <button onClick={() => setView("chat")}>Chatbot</button>
            <button
              onClick={() => setView("results")}
              disabled={!recommendation}
            >
              Kết quả
              {recommendation && <span>{scenarios.length}</span>}
            </button>
            <button className="active">Hồ sơ</button>
          </nav>
          <div className="header-actions">
            {profileSaved && <span className="saved-pill">ĐÃ LƯU</span>}
            <button
              className="header-button"
              onClick={() => {
                setView("chat");
                void loadDataSources();
              }}
            >
              Dữ liệu
            </button>
            <button className="header-button" onClick={() => setView("chat")}>
              ← Quay lại chatbot
            </button>
          </div>
        </header>

        <main className="profile-layout">
          <aside className="profile-nav">
            <span className="eyebrow">Dữ liệu đầu vào</span>
            <h1>Hồ sơ tài chính</h1>
            <p>
              Thông tin càng đầy đủ, các ràng buộc và phương án so sánh càng sát với hoàn cảnh của bạn.
            </p>
            <nav>
              {profileSections.map((section) => (
                <button
                  key={section.id}
                  className={activeProfileSection === section.id ? "active" : ""}
                  onClick={() => {
                    setActiveProfileSection(section.id);
                    document.getElementById(section.id)?.scrollIntoView({ behavior: "smooth" });
                  }}
                >
                  <span>{section.number}</span>
                  <div>
                    <strong>{section.label}</strong>
                    <small>{section.caption}</small>
                  </div>
                </button>
              ))}
            </nav>
            <div className="privacy-note">
              <strong>Dữ liệu được cô lập theo tài khoản</strong>
              <p>LLM không được tự tính hoặc sửa số liệu hồ sơ.</p>
            </div>
          </aside>

          <section className="profile-form">
            <div className="profile-intro">
              <div>
                <span className="eyebrow">Hồ sơ của {profile.display_name}</span>
                <h2>Xây nền cho một kế hoạch có thể giải thích.</h2>
              </div>
              <div className="profile-progress">
                <strong>5/5</strong>
                <span>nhóm dữ liệu</span>
              </div>
            </div>

            <section className="profile-section" id="demographics">
              <div className="section-title">
                <span>01</span>
                <div>
                  <h3>Nhân khẩu học</h3>
                  <p>Bối cảnh gia đình và độ ổn định thu nhập giúp hệ thống hiểu sức chịu đựng dài hạn.</p>
                </div>
              </div>
              <div className="profile-field-grid three">
                <label className="field">
                  <span>Tuổi</span>
                  <input type="number" min={18} max={100} value={profile.age}
                    onChange={(event) => updateProfile("age", Number(event.target.value))} />
                </label>
                <label className="field wide">
                  <span>Nghề nghiệp</span>
                  <input value={profile.occupation}
                    onChange={(event) => updateProfile("occupation", event.target.value)} />
                </label>
                <label className="field">
                  <span>Tình trạng hôn nhân</span>
                  <select value={profile.marital_status}
                    onChange={(event) => updateProfile("marital_status", event.target.value as Profile["marital_status"])}>
                    <option value="SINGLE">Độc thân</option>
                    <option value="MARRIED">Đã kết hôn</option>
                    <option value="DIVORCED">Ly hôn</option>
                    <option value="WIDOWED">Góa</option>
                  </select>
                </label>
                <label className="field">
                  <span>Số người phụ thuộc</span>
                  <input type="number" min={0} max={20} value={profile.dependents}
                    onChange={(event) => updateProfile("dependents", Number(event.target.value))} />
                </label>
                <label className="field">
                  <span>Ổn định việc làm</span>
                  <select value={profile.employment_stability}
                    onChange={(event) => updateProfile("employment_stability", event.target.value as Profile["employment_stability"])}>
                    <option value="LOW">Thấp / biến động</option>
                    <option value="MEDIUM">Trung bình</option>
                    <option value="HIGH">Cao / ổn định</option>
                  </select>
                </label>
              </div>
            </section>

            <section className="profile-section" id="financial">
              <div className="section-title">
                <span>02</span>
                <div>
                  <h3>Tài chính</h3>
                  <p>Dòng tiền, tài sản, nợ và bảo hiểm được dùng để đối soát vốn khả dụng.</p>
                </div>
              </div>
              <div className="profile-field-grid">
                <NumberField label="Thu nhập hàng tháng" value={profile.monthly_income}
                  onChange={(value) => updateProfile("monthly_income", value)} />
                <NumberField label="Chi tiêu hàng tháng" value={profile.monthly_expenses}
                  onChange={(value) => updateProfile("monthly_expenses", value)} />
                <NumberField label="Tiền tiết kiệm" value={profile.cash_savings}
                  onChange={(value) => updateProfile("cash_savings", value)} />
                <NumberField label="Tổng tài sản đang có" value={profile.total_assets}
                  onChange={(value) => updateProfile("total_assets", value)} />
                <NumberField label="Tổng dư nợ" value={profile.total_debt}
                  onChange={(value) => updateProfile("total_debt", value)} />
                <NumberField label="Trả nợ hàng tháng" value={profile.monthly_debt_payment}
                  onChange={(value) => updateProfile("monthly_debt_payment", value)} />
                <NumberField label="Quỹ dự phòng giữ riêng" value={profile.emergency_reserve}
                  onChange={(value) => updateProfile("emergency_reserve", value)} />
                <NumberField label="Nghĩa vụ gần hạn" value={profile.near_term_liabilities}
                  onChange={(value) => updateProfile("near_term_liabilities", value)} />
                <NumberField label="Quyền lợi bảo hiểm" value={profile.insurance_coverage}
                  onChange={(value) => updateProfile("insurance_coverage", value)} />
              </div>
            </section>

            <section className="profile-section" id="goals">
              <div className="section-title with-action">
                <span>03</span>
                <div>
                  <h3>Mục tiêu tài chính</h3>
                  <p>Mục tiêu đầu tiên là mục tiêu chính được optimizer dùng cho kỳ hạn kế hoạch.</p>
                </div>
                <button onClick={addGoal} disabled={profile.goals.length >= 10}>+ Thêm mục tiêu</button>
              </div>
              <div className="goal-list">
                {profile.goals.map((goalItem, index) => (
                  <article className="goal-card" key={goalItem.goal_id}>
                    <div className="goal-card-heading">
                      <span>MỤC TIÊU {String(index + 1).padStart(2, "0")}{index === 0 ? " · CHÍNH" : ""}</span>
                      <button onClick={() => removeGoal(index)} disabled={profile.goals.length === 1}>Xóa</button>
                    </div>
                    <div className="profile-field-grid three">
                      <label className="field wide">
                        <span>Tên mục tiêu</span>
                        <input value={goalItem.name}
                          onChange={(event) => updateGoal(index, "name", event.target.value)} />
                      </label>
                      <NumberField label="Số tiền mục tiêu" value={goalItem.target_amount}
                        onChange={(value) => updateGoal(index, "target_amount", value)} />
                      <label className="field">
                        <span>Thời hạn (tháng)</span>
                        <input type="number" min={1} max={600} value={goalItem.horizon_months}
                          onChange={(event) => updateGoal(index, "horizon_months", Number(event.target.value))} />
                      </label>
                      <label className="field">
                        <span>Mức ưu tiên</span>
                        <select value={goalItem.priority}
                          onChange={(event) => updateGoal(index, "priority", event.target.value as FinancialGoal["priority"])}>
                          <option value="LOW">Thấp</option>
                          <option value="MEDIUM">Trung bình</option>
                          <option value="HIGH">Cao</option>
                        </select>
                      </label>
                      <label className="field">
                        <span>Khả năng điều chỉnh</span>
                        <select value={goalItem.flexibility}
                          onChange={(event) => updateGoal(index, "flexibility", event.target.value as FinancialGoal["flexibility"])}>
                          <option value="FIXED">Cố định</option>
                          <option value="ADJUSTABLE">Có thể điều chỉnh</option>
                          <option value="FLEXIBLE">Linh hoạt</option>
                        </select>
                      </label>
                    </div>
                  </article>
                ))}
              </div>
            </section>

            <section className="profile-section" id="risk">
              <div className="section-title">
                <span>04</span>
                <div>
                  <h3>Rủi ro</h3>
                  <p>Phân biệt cảm xúc chấp nhận rủi ro và năng lực tài chính chịu rủi ro.</p>
                </div>
              </div>
              <div className="profile-field-grid three">
                <label className="field">
                  <span>Risk tolerance</span>
                  <select value={profile.risk_tolerance}
                    onChange={(event) => updateProfile("risk_tolerance", event.target.value as RiskCapacity)}>
                    <option value="LOW">Thấp</option>
                    <option value="MEDIUM">Trung bình</option>
                    <option value="HIGH">Cao</option>
                  </select>
                </label>
                <label className="field">
                  <span>Risk capacity</span>
                  <select value={profile.risk_capacity}
                    onChange={(event) => updateProfile("risk_capacity", event.target.value as RiskCapacity)}>
                    <option value="LOW">Thấp</option>
                    <option value="MEDIUM">Trung bình</option>
                    <option value="HIGH">Cao</option>
                  </select>
                </label>
                <label className="field">
                  <span>Sụt giảm tối đa chấp nhận (%)</span>
                  <input type="number" min={1} max={80} step={1}
                    value={Math.round(profile.max_acceptable_drawdown * 100)}
                    onChange={(event) => updateProfile("max_acceptable_drawdown", Number(event.target.value) / 100)} />
                </label>
              </div>
            </section>

            <section className="profile-section" id="convenience">
              <div className="section-title">
                <span>05</span>
                <div>
                  <h3>Thuận tiện quản lý</h3>
                  <p>Giới hạn độ phức tạp, tần suất theo dõi và mức khóa vốn bạn chấp nhận.</p>
                </div>
              </div>
              <div className="profile-field-grid three">
                <label className="field">
                  <span>Số sản phẩm tối đa</span>
                  <input type="number" min={1} max={20} value={profile.max_product_count}
                    onChange={(event) => updateProfile("max_product_count", Number(event.target.value))} />
                </label>
                <label className="field">
                  <span>Số ứng dụng/ngân hàng tối đa</span>
                  <input type="number" min={1} max={20} value={profile.max_financial_apps}
                    onChange={(event) => updateProfile("max_financial_apps", Number(event.target.value))} />
                </label>
                <label className="field">
                  <span>Tần suất theo dõi</span>
                  <select value={profile.monitoring_frequency}
                    onChange={(event) => updateProfile("monitoring_frequency", event.target.value as Profile["monitoring_frequency"])}>
                    <option value="DAILY">Hàng ngày</option>
                    <option value="WEEKLY">Hàng tuần</option>
                    <option value="MONTHLY">Hàng tháng</option>
                    <option value="QUARTERLY">Hàng quý</option>
                  </select>
                </label>
                <label className="field">
                  <span>Chấp nhận khóa vốn (tháng)</span>
                  <input type="number" min={0} max={120} value={profile.lockup_tolerance_months}
                    onChange={(event) => updateProfile("lockup_tolerance_months", Number(event.target.value))} />
                </label>
                <NumberField label="Nhu cầu thanh khoản" value={profile.liquidity_need}
                  onChange={(value) => updateProfile("liquidity_need", value)} />
                <label className="field">
                  <span>Cần thanh khoản trong (tháng)</span>
                  <input type="number" min={1} max={120} value={profile.liquidity_need_months}
                    onChange={(event) => updateProfile("liquidity_need_months", Number(event.target.value))} />
                </label>
              </div>
            </section>

            {error && <div className="profile-error">{error}</div>}
            <div className="profile-actions">
              <button className="secondary-action" onClick={saveProfile} disabled={profileSaving}>
                {profileSaving ? "Đang lưu…" : "Lưu hồ sơ"}
              </button>
              <button className="primary-action" onClick={saveAndAnalyze} disabled={profileSaving || loading || capital <= 0}>
                {loading ? "Đang chạy pipeline…" : "Lưu & phân tích ngay →"}
              </button>
            </div>
          </section>

          <aside className="profile-summary">
            <span className="eyebrow">Tóm tắt trực tiếp</span>
            <h3>Sức khỏe đầu vào</h3>
            <div className="summary-metric featured">
              <span>Vốn khả dụng</span>
              <strong>{money.format(Math.max(0, capital))}</strong>
              <small>Tài sản trừ dự phòng và nghĩa vụ gần hạn</small>
            </div>
            <div className="summary-metric">
              <span>Dòng tiền dư hàng tháng</span>
              <strong className={monthlySurplus < 0 ? "negative" : ""}>{money.format(monthlySurplus)}</strong>
            </div>
            <div className="summary-metric">
              <span>Tỷ lệ trả nợ / thu nhập</span>
              <strong>{profile.monthly_income ? pct(profile.monthly_debt_payment / profile.monthly_income) : "—"}</strong>
            </div>
            <div className="summary-metric">
              <span>Mục tiêu đang theo dõi</span>
              <strong>{profile.goals.length}</strong>
            </div>
            <div className="summary-guardrail">
              <span>OPTIMIZER GUARDRAIL</span>
              <p>Tối đa {profile.max_product_count} sản phẩm · khóa vốn không quá {profile.lockup_tolerance_months} tháng.</p>
            </div>
          </aside>
        </main>
      </div>
    );
  }

  return (
    <div className="app-shell">
      <header className="topbar">
        <div className="brand">
          <span className="brand-mark">M</span>
          <div>
            <strong>MONOPOLY AI</strong>
            <small>PORTFOLIO CONVERSATION LAB</small>
          </div>
        </div>
        <nav className="workspace-nav" aria-label="Không gian làm việc">
          <button
            className={view === "chat" ? "active" : ""}
            onClick={() => setView("chat")}
          >
            Chatbot
          </button>
          <button
            className={view === "results" ? "active" : ""}
            onClick={() => setView("results")}
          >
            Kết quả
            {recommendation && <span>{scenarios.length}</span>}
          </button>
          <button onClick={() => setView("profile")}>Hồ sơ</button>
        </nav>
        <div className="header-actions">
          <span className={`api-pill ${health?.llm_status || "fallback"}`}>
            <i />
            {health?.llm_status === "connected"
              ? `${health.llm_provider.toUpperCase()} · ${health.llm_model}`
              : "API CHƯA KẾT NỐI · FALLBACK"}
          </span>
          <button
            className={`data-pill ${health?.data_status === "OFFICIAL_DELAYED" ? "connected" : "fallback"}`}
            onClick={loadDataSources}
            disabled={dataLoading}
            title={`Snapshot: ${health?.data_snapshot || "chưa có"} · cập nhật ${dateTime(health?.data_last_updated || null)}`}
          >
            <i />
            {dataModeLabel(health?.data_status)}
            {health ? ` · ${health.data_sources_connected}/${health.data_sources_total}` : ""}
          </button>
          <button
            className={`mode-control ${
              request.requested_mode === "LICENSED_ADVISORY"
                ? "advisor-active"
                : "research-active"
            }`}
            onClick={openAdvisory}
            title="Chọn chế độ phát hành kết quả"
            aria-label={`Chế độ hiện tại: ${
              request.requested_mode === "LICENSED_ADVISORY"
                ? "Advisor được cấp phép"
                : "Nghiên cứu và giáo dục"
            }. Nhấn để thay đổi.`}
          >
            <span>CHẾ ĐỘ HIỆN TẠI</span>
            <strong>
              <i />
              {request.requested_mode === "LICENSED_ADVISORY"
                ? "ADVISOR · ĐƯỢC CẤP PHÉP"
                : "RESEARCH · GIÁO DỤC"}
            </strong>
            <em>Đổi</em>
          </button>
          <button className="header-button mobile-optional" onClick={openDepositComparison}>
            Lãi suất
          </button>
          <button className="header-button mobile-optional" onClick={loadAudit} disabled={!recommendation}>
            Audit
          </button>
          {authUser && (
            <button
              className="header-button user-session-button"
              onClick={logout}
              title={`${authUser.display_name} · ${authUser.email}`}
            >
              <span>{authUser.display_name}</span>
              <b>Thoát</b>
            </button>
          )}
        </div>
      </header>

      <main className={`advisor-layout ${view}-view`}>
        {false && <aside className="profile-panel">
          <div className="panel-heading">
            <div>
              <span className="eyebrow">Bối cảnh định lượng</span>
              <h2>Hồ sơ của bạn</h2>
            </div>
            <button className="close-profile" onClick={() => setView("chat")}>×</button>
          </div>
          <p className="panel-copy">
            AI dùng các dữ liệu này làm đầu vào. Mọi tỷ trọng đều do optimizer quyết định.
          </p>
          <form onSubmit={runPlan}>
            <NumberField
              label="Tổng tài sản"
              value={profile.total_assets}
              onChange={(value) => updateProfile("total_assets", value)}
            />
            <div className="field-grid">
              <NumberField
                label="Quỹ dự phòng"
                value={profile.emergency_reserve}
                onChange={(value) => updateProfile("emergency_reserve", value)}
              />
              <NumberField
                label="Nghĩa vụ gần hạn"
                value={profile.near_term_liabilities}
                onChange={(value) => updateProfile("near_term_liabilities", value)}
              />
            </div>
            <label className="field">
              <span>Mục tiêu</span>
              <textarea
                rows={3}
                value={profile.goal}
                onChange={(event) => updateProfile("goal", event.target.value)}
              />
            </label>
            <div className="field-grid">
              <label className="field">
                <span>Thời hạn (tháng)</span>
                <input
                  type="number"
                  min={1}
                  max={600}
                  value={profile.horizon_months}
                  onChange={(event) =>
                    updateProfile("horizon_months", Number(event.target.value))
                  }
                />
              </label>
              <label className="field">
                <span>Khả năng chịu rủi ro</span>
                <select
                  value={profile.risk_capacity}
                  onChange={(event) =>
                    updateProfile("risk_capacity", event.target.value as RiskCapacity)
                  }
                >
                  <option value="LOW">Thấp</option>
                  <option value="MEDIUM">Trung bình</option>
                  <option value="HIGH">Cao</option>
                </select>
              </label>
            </div>
            <NumberField
              label={`Cần thanh khoản trong ${profile.liquidity_need_months} tháng`}
              value={profile.liquidity_need}
              onChange={(value) => updateProfile("liquidity_need", value)}
            />
            <div className="capital-readout">
              <span>Vốn khả dụng</span>
              <strong>{money.format(Math.max(0, capital))}</strong>
              <small>Đã trừ dự phòng và nghĩa vụ gần hạn</small>
            </div>
            {error && <div className="error-box">{error}</div>}
            <button className="primary-button" disabled={loading || capital <= 0}>
              {loading ? "Đang chạy pipeline 13 bước…" : recommendation ? "Phân tích lại hồ sơ" : "Phân tích ngay"}
            </button>
          </form>
          <div className="trust-note">
            <span>LEGAL GATE</span>
            <span>CP-SAT</span>
            <span>RISK ENGINE</span>
            <span>OUTPUT POLICY</span>
          </div>
        </aside>}

        {view === "chat" && (
        <>
          <aside className="chat-history-sidebar">
            <h3>Lịch sử trò chuyện</h3>
            {historySessions.length === 0 ? (
              <span style={{fontSize: 12, color: "var(--text-light)"}}>Chưa có phiên nào.</span>
            ) : (
              historySessions.map((session) => (
                <div key={session.recommendation_id} className="history-session" onClick={() => loadSession(session.recommendation_id)}>
                  <strong>{session.goal || "Chưa đặt tên"}</strong>
                  <span>{new Date(session.created_at).toLocaleDateString("vi-VN")} · {session.scenario_count} phương án</span>
                </div>
              ))
            )}
          </aside>
          <section className="conversation-panel">
          <div className="conversation-heading">
            <div>
              <span className="eyebrow">Trợ lý chính</span>
              <h1>Hỏi bằng ngôn ngữ tự nhiên.<br />Kiểm chứng bằng số liệu.</h1>
            </div>
            <div className="conversation-status">
              <span className="pulse" />
              {chatLoading ? "Đang diễn giải…" : "Sẵn sàng đối thoại"}
            </div>
          </div>

          <div
            className={`mode-context-banner ${
              request.requested_mode === "LICENSED_ADVISORY"
                ? "advisor"
                : "research"
            }`}
          >
            <div>
              <span className="mode-context-icon">
                {request.requested_mode === "LICENSED_ADVISORY" ? "A" : "R"}
              </span>
              <p>
                <strong>
                  {request.requested_mode === "LICENSED_ADVISORY"
                    ? "Bạn đang ở chế độ Advisor"
                    : "Bạn đang ở chế độ Research"}
                </strong>
                <span>
                  {request.requested_mode === "LICENSED_ADVISORY"
                    ? "Câu trả lời dùng investment memo toàn cảnh: hồ sơ, định lượng, sản phẩm, thị trường, vĩ mô, kỹ thuật, rủi ro và điều kiện thực hiện."
                    : "Hệ thống chỉ so sánh và giáo dục; không phát hành khuyến nghị cấp sản phẩm cá nhân hóa."}
                </span>
              </p>
            </div>
            {recommendation &&
              ((request.requested_mode === "LICENSED_ADVISORY") !==
                (recommendation.released_output.output_release_type ===
                  "ADVISORY_SELECTED")) && (
                <small>
                  Kết quả đang xem được tạo ở chế độ trước. Hãy phân tích lại hồ sơ
                  để áp dụng chế độ mới.
                </small>
              )}
            <button type="button" onClick={openAdvisory}>
              Đổi chế độ
            </button>
          </div>

          <div className="message-list" ref={messageListRef} aria-live="polite">
            {messages.map((message) => (
              <article className={`message ${message.role}`} key={message.id}>
                <div className="avatar">{message.role === "assistant" ? "AI" : "BẠN"}</div>
                <div className="message-body">
                  <p>{message.text}</p>
                  {message.sections?.map((section, index) => (
                    <div className="answer-section" key={`${section.title}-${index}`}>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <div>
                        <strong>{section.title}</strong>
                        <p>{section.body}</p>
                      </div>
                    </div>
                  ))}
                  {message.generatedBy && (
                    <small className="generated-label">
                      {message.generatedBy === "GROQ_STRUCTURED_OUTPUT"
                        ? "Hội thoại bởi Groq · không tự tính số liệu"
                        : message.generatedBy === "OPENAI_STRUCTURED_OUTPUT"
                          ? "Hội thoại bởi OpenAI · không tự tính số liệu"
                          : message.generatedBy === "DATA_REGISTRY"
                            ? "Tính toán deterministic · dữ liệu từ registry"
                            : "Diễn giải dự phòng deterministic"}
                    </small>
                  )}
                </div>
              </article>
            ))}
            {chatLoading && (
              <article className="message assistant typing-message">
                <div className="avatar">AI</div>
                <div className="typing"><i /><i /><i /></div>
              </article>
            )}
          </div>

          <div className="conversation-footer">
            <div className="suggestion-row">
              {suggestions.slice(0, 4).map((suggestion) => (
                <button
                  key={suggestion}
                  type="button"
                  onClick={() => ask(suggestion)}
                  disabled={loading || chatLoading}
                >
                  {suggestion}
                </button>
              ))}
            </div>
            <form className="composer" onSubmit={sendChat}>
              <textarea
                value={chatInput}
                onChange={(event) => setChatInput(event.target.value)}
                onKeyDown={(event) => {
                  if (event.key === "Enter" && !event.shiftKey) {
                    event.preventDefault();
                    event.currentTarget.form?.requestSubmit();
                  }
                }}
                rows={2}
                placeholder={
                  recommendation
                    ? "Ví dụ: Vì sao phương án cân bằng phù hợp hơn? Nếu tôi cần rút 20 triệu trong 3 tháng thì sao?"
                    : "Hỏi về cách hệ thống hoạt động hoặc bấm “Hãy phân tích hồ sơ mẫu”…"
                }
              />
              <button disabled={!chatInput.trim() || loading || chatLoading} aria-label="Gửi">
                <span>Gửi</span> ↗
              </button>
            </form>
            <p className="composer-note">
              Không phải tư vấn đầu tư · Không cam kết lợi nhuận · Không đặt lệnh tự động
            </p>
          </div>
        </section>
        </>
        )}

        {view === "results" && (
        <>
        <div className="results-page-heading">
          <div>
            <span className="eyebrow">Portfolios / Allocation analysis</span>
            <h1>Kết quả phân tích danh mục</h1>
            <p>
              So sánh phương án, kiểm tra phân bổ và truy vết từng giả định từ
              optimizer.
            </p>
          </div>
          <div className="results-heading-actions">
            <span className={recommendation ? "result-ready" : "result-pending"}>
              {recommendation
                ? `${recommendation.released_output.output_release_type} · SẴN SÀNG`
                : "CHƯA CÓ KẾT QUẢ"}
            </span>
            <button onClick={() => setView("chat")}>Trao đổi với AI</button>
            <button
              className="primary"
              onClick={() => runPlan()}
              disabled={loading}
            >
              {loading ? "Đang phân tích…" : recommendation ? "Phân tích lại" : "Phân tích ngay"}
            </button>
          </div>
        </div>
        <aside className="insight-panel" ref={insightPanelRef}>
          {!recommendation ? (
            <div className="insight-empty">
              <span className="eyebrow">Bằng chứng trực tiếp</span>
              <h2>Chưa có kết quả phân tích.</h2>
              <p>
                Chạy hồ sơ hiện tại để xem phân bổ, rủi ro, stress test và lý do
                khác biệt giữa từng phương án.
              </p>
              <button onClick={() => runPlan()} disabled={loading}>
                {loading ? "Đang phân tích…" : "Dùng hồ sơ mẫu"}
              </button>
              <div className="empty-proof">
                <div><strong>13</strong><span>bước có audit trail</span></div>
                <div><strong>3</strong><span>phương án độc lập</span></div>
                <div><strong>0</strong><span>con số do LLM tự tính</span></div>
              </div>
            </div>
          ) : recommendation.released_output.output_release_type === "BLOCKED" ? (
            <div className="insight-empty blocked">
              <span className="eyebrow">Compliance Gate</span>
              <h2>Kết quả bị chặn.</h2>
              <p>{recommendation.released_output.blocked_message}</p>
            </div>
          ) : scenario ? (
            <>
              <div className="insight-controls">
                <div className="insight-heading">
                  <div>
                    <span className="eyebrow">
                      {scenario.recommendation_role === "RECOMMENDED"
                        ? "Phương án khuyến nghị"
                        : scenario.recommendation_role === "ALTERNATIVE"
                          ? "Phương án thay thế"
                          : "Phương án đang giải thích"}
                    </span>
                    <h2>{scenario.name}</h2>
                  </div>
                  <button className="report-link" onClick={downloadReport}>
                    PDF ↗
                  </button>
                </div>

                <div className="scenario-tabs" role="tablist">
                  {scenarios.map((item, index) => (
                    <button
                      key={item.scenario_id}
                      className={index === activeScenario ? "active" : ""}
                      aria-selected={index === activeScenario}
                      role="tab"
                      onClick={() => setActiveScenario(index)}
                    >
                      <span>0{index + 1}</span>
                      {item.recommendation_role && (
                        <em>
                          {item.recommendation_role === "RECOMMENDED"
                            ? "KHUYẾN NGHỊ"
                            : "THAY THẾ"}
                        </em>
                      )}
                      <strong>{item.name.replace(" có kiểm soát", "")}</strong>
                      <small>{pct(item.expected_return_rate)}</small>
                    </button>
                  ))}
                </div>
              </div>

              <div className="metric-grid">
                <article>
                  <span>Lợi nhuận kỳ vọng</span>
                  <strong>{pct(scenario.expected_return_rate)}</strong>
                  <small>{money.format(scenario.expected_return_amount)} / năm</small>
                </article>
                <article>
                  <span>Biến động</span>
                  <strong>{pct(scenario.risk_metrics.annualized_volatility)}</strong>
                  <small>Trần {pct(scenario.risk_metrics.risk_ceiling)}</small>
                </article>
                <article>
                  <span>VaR 95%</span>
                  <strong>{compactMoney(scenario.risk_metrics.var_95_amount)}</strong>
                  <small>Ước tính mô hình</small>
                </article>
                <article>
                  <span>Thanh khoản</span>
                  <strong>{scenario.risk_metrics.liquidity_score.toFixed(1)}</strong>
                  <small>thang 0–100</small>
                </article>
                <article className={scenario.fragmentation_warning ? "metric-warning" : ""}>
                  <span>Độ phức tạp vận hành</span>
                  <strong>{scenario.operational_complexity_score.toFixed(1)}</strong>
                  <small>0 dễ quản lý · 100 bất tiện</small>
                </article>
              </div>

              <article className={`evidence-card complexity-card ${scenario.fragmentation_warning ? "warning" : ""}`}>
                <div className="card-heading">
                  <div>
                    <span>Operational complexity · 4th objective</span>
                    <strong>Chi phí theo dõi ngoài lợi nhuận, rủi ro và thanh khoản</strong>
                  </div>
                  <em>{scenario.complexity_config_version}</em>
                </div>
                <div className="complexity-summary">
                  <strong>{scenario.operational_complexity_score.toFixed(1)}/100</strong>
                  <p>
                    {scenario.complexity_breakdown.distinct_product_count} sản phẩm tại{" "}
                    {scenario.complexity_breakdown.distinct_provider_count} tổ chức ·{" "}
                    {scenario.complexity_breakdown.fragment_product_count} phần dưới ngưỡng phân mảnh ·{" "}
                    {scenario.complexity_breakdown.distinct_maturity_count} kỳ hạn cần theo dõi.
                  </p>
                </div>
                <div className="complexity-breakdown">
                  <div><span>Sản phẩm</span><b>{scenario.complexity_breakdown.distinct_product_count}</b></div>
                  <div><span>Tổ chức/app</span><b>{scenario.complexity_breakdown.distinct_provider_count}</b></div>
                  <div><span>Phân bổ vụn</span><b>{scenario.complexity_breakdown.fragment_product_count}</b></div>
                  <div><span>Phần nhỏ nhất</span><b>{money.format(scenario.complexity_breakdown.smallest_allocation_amount)}</b></div>
                </div>
                {scenario.fragmentation_warning && (
                  <p className="fragmentation-warning">
                    {recommendation.released_output.legal_operating_mode === "RESEARCH_EDUCATION"
                      ? "COMPARE_ONLY: vốn nhỏ đang được chia qua nhiều điểm chạm; có thể dùng phép so sánh gộp để xem mức đánh đổi, không phải chỉ dẫn thực hiện."
                      : "Độ phân mảnh vượt ngưỡng cấu hình; re-solve sẽ giữ nguyên risk/liquidity gate và chỉ cập nhật phương án này."}
                  </p>
                )}
                {scenario.complexity_resolve_count > 0 && (
                  <p className="complexity-delta">
                    Lần gộp {scenario.complexity_resolve_count}/3 · delta lợi nhuận kỳ vọng{" "}
                    <strong>{money.format(scenario.complexity_return_delta_amount)}/năm</strong>{" "}
                    ({pct(scenario.complexity_return_delta_rate)}).
                  </p>
                )}
                <button
                  className="complexity-action"
                  type="button"
                  onClick={consolidateActiveScenario}
                  disabled={
                    complexityLoadingId === scenario.scenario_id ||
                    scenario.complexity_resolve_count >= 3
                  }
                >
                  {complexityLoadingId === scenario.scenario_id
                    ? "Đang re-solve…"
                    : scenario.complexity_resolve_count >= 3
                      ? "Đã đạt giới hạn 3 lần"
                      : "Gộp bớt sản phẩm cho kịch bản này"}
                </button>
              </article>

              <article className="evidence-card allocation-card">
                <div className="card-heading">
                  <div>
                    <span>Phân bổ được phát hành</span>
                    <strong>
                      {scenario.allocation_granularity === "PRODUCT"
                        ? "Sản phẩm, số tiền và điều kiện thực hiện"
                        : "Số tiền và lý do theo từng nhóm tài sản"}
                    </strong>
                  </div>
                  <em>
                    {recommendation.released_output.output_release_type === "ADVISORY_SELECTED"
                      ? "ADVISORY"
                      : "COMPARE ONLY"}
                  </em>
                </div>
                <p className="allocation-context">
                  Vốn khả dụng {money.format(scenario.investable_capital)}
                  {recommendation.released_output.financial_plan
                    ? ` · cần giữ ${money.format(
                        recommendation.released_output.financial_plan.immediate_liquidity_bucket
                      )} trong vùng thanh khoản tức thời`
                    : ""}
                  {` · trần rủi ro ${pct(scenario.risk_metrics.risk_ceiling)}`}.
                </p>
                <div className="allocation-list">
                  {[...scenario.allocations]
                    .sort((a, b) => b.amount - a.amount)
                    .map((item) => {
                      const detail = scenario.allocation_explanations?.find(
                        (candidate) =>
                          item.product_id
                            ? candidate.product_id === item.product_id
                            : candidate.asset_class === item.asset_class
                      );
                      return (
                        <div className="allocation-row" key={item.product_id || item.asset_class}>
                          <div>
                            <i style={{ background: COLORS[item.asset_class] || "#71827c" }} />
                            <span>
                              {item.asset_class === "GOLD" && item.product_id
                                ? item.product_id.includes("sjc")
                                  ? "Vàng miếng SJC 999.9"
                                  : "Vàng nhẫn tròn PNJ 999.9"
                                : item.product_name ||
                                  ASSET_LABELS[item.asset_class] ||
                                  item.asset_class}
                              {item.provider ? ` · ${item.provider}` : ""}
                            </span>
                            <strong>{pct(item.weight)}</strong>
                          </div>
                          <div className="allocation-track">
                            <span
                              style={{
                                width: `${Math.max(2, item.weight * 100)}%`,
                                background: COLORS[item.asset_class] || "#71827c"
                              }}
                            />
                          </div>
                          <small>
                            {item.asset_class === "GOLD" &&
                            item.estimated_units &&
                            item.reference_price
                              ? `${item.estimated_units} ${
                                  item.product_id?.includes("sjc") ? "lượng" : "chỉ"
                                } × ${money.format(item.reference_price)} = ${money.format(
                                  item.amount
                                )}`
                              : money.format(item.amount)}
                            {" · đóng góp kỳ vọng "}
                            {money.format(item.expected_return_amount)}/năm
                          </small>
                          {detail && (
                            <div className="allocation-explanation">
                              <p><strong>Vai trò</strong>{detail.portfolio_role}</p>
                              <p><strong>Vì sao chọn và hình thành tỷ trọng</strong>{detail.allocation_reason}</p>
                              <p><strong>Lợi nhuận và rủi ro</strong>{detail.expected_return_and_risk}</p>
                              <p><strong>Chi phí và thanh khoản</strong>{detail.cost_and_liquidity}</p>
                              <p><strong>Điều kiện thực hiện</strong>{detail.execution_conditions.join(" ")}</p>
                              <p><strong>Kịch bản bất lợi</strong>{detail.adverse_scenario}</p>
                              <p><strong>Nguồn và thời điểm</strong>{detail.data_evidence.join(" ")}</p>
                              <p><strong>Điểm giới hạn</strong>{detail.limiting_factor}</p>
                              <p><strong>Giả định/điều kiện tính lại</strong>
                                {[...detail.result_sensitive_assumptions, detail.change_trigger].join(" ")}
                              </p>
                            </div>
                          )}
                          {item.asset_class === "GOLD" && item.product_id && (
                            <div className="gold-implementation">
                              <strong>Sản phẩm vàng vật chất</strong>
                              <span>
                                {item.product_id.includes("sjc")
                                  ? `${item.estimated_units ?? 0} lượng × ${
                                      item.reference_price
                                        ? money.format(item.reference_price)
                                        : "chưa có đơn giá"
                                    }`
                                  : `${item.estimated_units ?? 0} chỉ × ${
                                      item.reference_price
                                        ? money.format(item.reference_price)
                                        : "chưa có đơn giá"
                                    }`}
                              </span>
                              <small>
                                Đơn giá mua cho mỗi {item.product_id.includes("sjc") ? "lượng" : "chỉ"}:{" "}
                                {item.reference_price
                                  ? money.format(item.reference_price)
                                  : "chưa có"}
                                {` · tổng vốn ${money.format(item.amount)} · chênh lệch mua–bán ước tính ${money.format(
                                  item.transaction_cost_amount
                                )}`}
                              </small>
                              <em>Đối chiếu cùng chart COMEX, USD/VND, DXY và lợi suất thực Mỹ trong chatbot.</em>
                            </div>
                          )}
                          {item.asset_class === "DEPOSIT" &&
                            scenario.deposit_implementation.length > 0 && (
                              <div className="deposit-implementation">
                                <div className="deposit-implementation-title">
                                  <strong>Ngân hàng · kỳ hạn · số vốn cụ thể</strong>
                                  <span>{scenario.deposit_implementation.length} khoản</span>
                                </div>
                                {scenario.deposit_implementation.map((deposit) => (
                                  <article key={deposit.product_id}>
                                    <div>
                                      <strong>{deposit.bank}</strong>
                                      <span>
                                        {deposit.tenor_months
                                          ? `${deposit.tenor_months} tháng`
                                          : "Xác nhận kỳ hạn"}
                                      </span>
                                    </div>
                                    <b>{money.format(deposit.amount)}</b>
                                    <dl>
                                      <div>
                                        <dt>Lãi suất</dt>
                                        <dd>{pct(deposit.annual_rate)}/năm</dd>
                                      </div>
                                      <div>
                                        <dt>Lãi cuối kỳ</dt>
                                        <dd>
                                          {deposit.term_interest_amount !== null
                                            ? money.format(deposit.term_interest_amount)
                                            : "Cần xác nhận"}
                                        </dd>
                                      </div>
                                      <div>
                                        <dt>Đáo hạn</dt>
                                        <dd>
                                          {deposit.maturity_amount !== null
                                            ? money.format(deposit.maturity_amount)
                                            : "Cần xác nhận"}
                                        </dd>
                                      </div>
                                    </dl>
                                    <p>{deposit.why_selected}</p>
                                    <small>{deposit.conditions.join(" ")}</small>
                                    <time>Cập nhật {dateTime(deposit.data_timestamp)}</time>
                                  </article>
                                ))}
                              </div>
                            )}
                        </div>
                      );
                    })}
                </div>
              </article>

              <article className="evidence-card why-card">
                <div className="card-heading">
                  <div>
                    <span>Giải thích có cấu trúc</span>
                    <strong>Vì sao phương án này khác?</strong>
                  </div>
                  <em>{recommendation.explanation.confidence}%</em>
                </div>
                {scenarioInsights.map((item, index) => (
                  <div className="why-row" key={item.label}>
                    <span>{String(index + 1).padStart(2, "0")}</span>
                    <div>
                      <strong>{item.label}</strong>
                      <p>{item.text}</p>
                    </div>
                  </div>
                ))}
              </article>

              <article className="evidence-card advisory-detail-card">
                <div className="card-heading">
                  <div>
                    <span>Theo dõi sau khi ghi nhận</span>
                    <strong>7 điều kiện kích hoạt tính toán lại</strong>
                  </div>
                  <em>5 PP DRIFT</em>
                </div>
                <div className="trigger-list">
                  {scenario.monitoring_triggers.map((trigger, index) => (
                    <div key={trigger.trigger_type}>
                      <span>{String(index + 1).padStart(2, "0")}</span>
                      <p>
                        <strong>{trigger.trigger_condition}</strong>
                        {trigger.current_reference} {trigger.action}
                      </p>
                    </div>
                  ))}
                </div>
              </article>

              <article className="evidence-card advisory-detail-card">
                <div className="card-heading">
                  <div>
                    <span>Khi cần rút vốn</span>
                    <strong>So sánh chi phí và ảnh hưởng phần còn lại</strong>
                  </div>
                  <em>4 OPTIONS</em>
                </div>
                <div className="withdrawal-list">
                  {[...scenario.withdrawal_options]
                    .sort((a, b) => a.priority - b.priority)
                    .map((option) => (
                      <div key={option.option_type}>
                        <span>Ưu tiên {option.priority}</span>
                        <strong>{option.title}</strong>
                        <b>{money.format(option.available_amount)}</b>
                        <p><em>Chi phí:</em> {option.estimated_cost}</p>
                        <p><em>Tác động:</em> {option.portfolio_impact}</p>
                        <small>{option.conditions.join(" ")}</small>
                      </div>
                    ))}
                </div>
              </article>

              {recommendation.released_output.output_release_type === "ADVISORY_SELECTED" &&
                (scenario.selection_decisions?.length || recommendation.released_output.selection_decisions) && (
                  <article className="evidence-card advisory-detail-card">
                    <div className="card-heading">
                      <div>
                        <span>Eligibility & selection</span>
                        <strong>Vì sao sản phẩm được chọn hoặc bị loại</strong>
                      </div>
                    </div>
                    <div className="decision-list">
                      {(scenario.selection_decisions?.length
                        ? scenario.selection_decisions
                        : recommendation.released_output.selection_decisions || [])
                        .slice()
                        .sort((a, b) => {
                          const priority = (item: typeof a) =>
                            item.status === "SELECTED_INTERNAL"
                              ? 0
                              : item.asset_class === "GOLD"
                                ? 1
                                : item.status === "ELIGIBLE_NOT_SELECTED"
                                  ? 2
                                  : 3;
                          return priority(a) - priority(b);
                        })
                        .slice(0, 18)
                        .map((decision) => (
                          <div key={decision.product_id}>
                            <span className={decision.status.toLowerCase()}>
                              {decision.status === "SELECTED_INTERNAL"
                                ? "ĐƯỢC CHỌN"
                                : decision.status === "REJECTED"
                                  ? "BỊ LOẠI"
                                  : "ĐỦ ĐK · KHÔNG CHỌN"}
                            </span>
                            <div className="decision-copy">
                              <strong>
                                {readableProductName(decision.product_id, decision.product_name)}
                              </strong>
                              <small>
                                {decision.provider || "Nhà cung cấp chưa công bố"} ·{" "}
                                {ASSET_LABELS[decision.asset_class] || decision.asset_class}
                              </small>
                              <p>{decision.reasons.join(" ")}</p>
                              <div className="decision-metrics">
                                {decision.expected_return != null && (
                                  <span>Lợi nhuận mô hình <b>{pct(decision.expected_return)}/năm</b></span>
                                )}
                                {decision.volatility != null && (
                                  <span>Biến động <b>{pct(decision.volatility)}</b></span>
                                )}
                                {decision.liquidity_score != null && (
                                  <span>Thanh khoản <b>{decision.liquidity_score}/100</b></span>
                                )}
                                {decision.minimum_investment != null && (
                                  <span>Tối thiểu <b>{money.format(decision.minimum_investment)}</b></span>
                                )}
                                {decision.lockup_period_days != null && (
                                  <span>Khóa vốn <b>{decision.lockup_period_days} ngày</b></span>
                                )}
                              </div>
                              <code>{decision.reason_codes.join(" · ")}</code>
                              <code>{decision.product_id}</code>
                            </div>
                          </div>
                        ))}
                    </div>
                  </article>
                )}

              <article className="evidence-card guardrail-card">
                <span>RANH GIỚI PHÁT HÀNH</span>
                <p>
                  {recommendation.released_output.output_release_type === "ADVISORY_SELECTED"
                    ? "Chi tiết cấp sản phẩm chỉ được phát hành vì bằng chứng pháp lý advisory đã được xác minh. Mọi thao tác vẫn cần xác nhận của con người."
                    : "Chi tiết số tiền theo từng sản phẩm được giữ nội bộ. Chỉ phát hành ở cấp nhóm tài sản do hệ thống đang ở chế độ COMPARE_ONLY."}
                </p>
                <code>{recommendation.released_output.recommendation_id}</code>
              </article>
              
              <div style={{ marginTop: "24px" }}>
                <button 
                  onClick={downloadReport} 
                  style={{
                    padding: "14px 24px",
                    background: "var(--green)",
                    color: "#fff",
                    border: "none",
                    borderRadius: "8px",
                    fontWeight: 700,
                    width: "100%",
                    fontSize: "13px",
                    cursor: "pointer",
                    boxShadow: "0 4px 12px rgba(33, 91, 75, 0.2)",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    gap: "8px"
                  }}
                >
                  📥 Tải Báo Cáo PDF Khuyến Nghị
                </button>
              </div>
            </>
          ) : null}
        </aside>
        </>
        )}
      </main>

      {showAdvisory && (
        <div className="modal-backdrop" onClick={() => setShowAdvisory(false)}>
          <div
            className="audit-modal advisor-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-title">
              <div>
                <span className="eyebrow">Compliance-controlled output</span>
                <h3>Chế độ Advisor</h3>
                <p>
                  Advisor phát hành một phương án khuyến nghị và hai phương án
                  thay thế ở cấp sản phẩm, kèm số tiền, điều kiện thực hiện và
                  trách nhiệm của chuyên viên phụ trách.
                </p>
              </div>
              <button onClick={() => setShowAdvisory(false)}>Đóng</button>
            </div>

            <div
              className={`advisor-status-card ${
                advisoryStatus?.authorized ? "authorized" : ""
              }`}
            >
              <strong>
                {advisoryStatus?.authorized
                  ? "Đã đủ điều kiện phát hành Advisor"
                  : "Chưa đủ điều kiện phát hành Advisor"}
              </strong>
              <span>
                {advisoryStatus?.authorized
                  ? `Xác minh bởi ${
                      advisoryStatus.verified_by || "quản trị viên"
                    } · ${dateTime(advisoryStatus.verified_at)}`
                  : "Cần xác minh đủ cả ba điều kiện pháp lý bên dưới."}
              </span>
            </div>

            <div className="mode-choice-grid" aria-label="Chọn chế độ phân tích">
              <button
                type="button"
                className={
                  request.requested_mode === "RESEARCH_EDUCATION"
                    ? "selected research"
                    : "research"
                }
                onClick={useResearchMode}
              >
                <span>RESEARCH</span>
                <strong>Nghiên cứu & giáo dục</strong>
                <small>
                  So sánh phương án, giải thích nhóm tài sản, không phát hành
                  khuyến nghị sản phẩm cá nhân hóa.
                </small>
                <b>
                  {request.requested_mode === "RESEARCH_EDUCATION"
                    ? "✓ ĐANG SỬ DỤNG"
                    : "CHỌN CHẾ ĐỘ NÀY"}
                </b>
              </button>
              <button
                type="button"
                className={
                  request.requested_mode === "LICENSED_ADVISORY"
                    ? "selected advisor"
                    : "advisor"
                }
                onClick={useAdvisoryMode}
                disabled={!advisoryStatus?.authorized}
              >
                <span>ADVISOR</span>
                <strong>Tư vấn được cấp phép</strong>
                <small>
                  Phát hành một khuyến nghị và hai lựa chọn thay thế, kèm luận
                  điểm đầu tư toàn cảnh và điều kiện thực hiện.
                </small>
                <b>
                  {!advisoryStatus?.authorized
                    ? "CHƯA ĐỦ ĐIỀU KIỆN"
                    : request.requested_mode === "LICENSED_ADVISORY"
                      ? "✓ ĐANG SỬ DỤNG"
                      : "CHỌN CHẾ ĐỘ NÀY"}
                </b>
              </button>
            </div>

            <div className="advisor-check-list">
              <label className="advisor-check">
                <input
                  type="checkbox"
                  checked={advisoryDraft.licensed_entity_verified}
                  disabled={!advisoryStatus?.can_manage}
                  onChange={(event) =>
                    setAdvisoryDraft((current) => ({
                      ...current,
                      licensed_entity_verified: event.target.checked
                    }))
                  }
                />
                <div>
                  <strong>Đơn vị có giấy phép phù hợp</strong>
                  <span>
                    Pháp nhân chịu trách nhiệm đã được kiểm tra giấy phép và phạm
                    vi cung cấp dịch vụ.
                  </span>
                </div>
              </label>
              <label className="advisor-check">
                <input
                  type="checkbox"
                  checked={advisoryDraft.advisory_contract_verified}
                  disabled={!advisoryStatus?.can_manage}
                  onChange={(event) =>
                    setAdvisoryDraft((current) => ({
                      ...current,
                      advisory_contract_verified: event.target.checked
                    }))
                  }
                />
                <div>
                  <strong>Hợp đồng tư vấn đã có hiệu lực</strong>
                  <span>
                    Quan hệ tư vấn, phạm vi trách nhiệm và điều khoản sử dụng đã
                    được ghi nhận.
                  </span>
                </div>
              </label>
              <label className="advisor-check">
                <input
                  type="checkbox"
                  checked={advisoryDraft.responsible_advisor_verified}
                  disabled={!advisoryStatus?.can_manage}
                  onChange={(event) =>
                    setAdvisoryDraft((current) => ({
                      ...current,
                      responsible_advisor_verified: event.target.checked
                    }))
                  }
                />
                <div>
                  <strong>Chuyên viên phụ trách đã được chỉ định</strong>
                  <span>
                    Có người chịu trách nhiệm rà soát hồ sơ và phê duyệt kết quả
                    trước khi thực hiện.
                  </span>
                </div>
              </label>
            </div>

            <p className="data-disclaimer">
              {advisoryStatus?.can_manage
                ? "Bạn đang dùng tài khoản quản trị. Việc đánh dấu là một xác nhận nghiệp vụ và được lưu vào hệ thống."
                : "Tài khoản thường không thể tự mở Advisor. Quản trị viên hoặc bộ phận tuân thủ phải xác minh các điều kiện này."}
            </p>

            <div className="advisor-actions">
              <button onClick={() => setShowAdvisory(false)}>Đóng</button>
              {advisoryStatus?.can_manage && (
                <button
                  className="primary-action"
                  onClick={saveAdvisoryStatus}
                  disabled={advisorySaving}
                >
                  {advisorySaving
                    ? "Đang xác minh…"
                    : advisoryDraft.licensed_entity_verified &&
                        advisoryDraft.advisory_contract_verified &&
                        advisoryDraft.responsible_advisor_verified
                      ? "Lưu & bật Advisor"
                      : advisoryStatus?.authorized
                        ? "Lưu & thu hồi Advisor"
                        : "Lưu trạng thái"}
                </button>
              )}
            </div>
          </div>
        </div>
      )}

      {showAudit && (
        <div className="modal-backdrop" onClick={() => setShowAudit(false)}>
          <div className="audit-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-title">
              <div>
                <span className="eyebrow">Audit trail</span>
                <h3>13 bước có thể truy vết</h3>
              </div>
              <button onClick={() => setShowAudit(false)}>Đóng</button>
            </div>
            <div className="audit-list">
              {audit.map((row, index) => (
                <div key={String(row.audit_id)}>
                  <span>{String(index + 1).padStart(2, "0")}</span>
                  <div>
                    <strong>{String(row.module_name)}</strong>
                    <small>{String(row.event_type)}</small>
                  </div>
                  <time>{String(row.created_at)}</time>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}

      {showDataSources && dataSummary && (
        <div className="modal-backdrop" onClick={() => setShowDataSources(false)}>
          <div className="audit-modal data-modal" onClick={(event) => event.stopPropagation()}>
            <div className="modal-title">
              <div>
                <span className="eyebrow">Data provenance</span>
                <h3>Nguồn dữ liệu và độ mới</h3>
                <p>
                  Snapshot <code>{dataSummary.snapshot_id}</code> ·{" "}
                  {dataSummary.connected_sources}/{dataSummary.total_sources} nguồn đang hoạt động
                </p>
              </div>
              <div className="modal-actions">
                {authUser?.role === "admin" && (
                  <button onClick={refreshDataSources} disabled={dataLoading}>
                    {dataLoading ? "Đang đồng bộ…" : "Đồng bộ ngay"}
                  </button>
                )}
                <button onClick={() => setShowDataSources(false)}>Đóng</button>
              </div>
            </div>
            <div className="data-source-list">
              {dataSummary.sources.map((source) => (
                <article key={source.source_id}>
                  <span className={`source-status ${source.operational_status.toLowerCase()}`}>
                    {source.operational_status === "CONNECTED"
                      ? "Đã kết nối"
                      : source.operational_status === "STALE_FALLBACK"
                        ? "Dùng snapshot gần nhất"
                        : source.operational_status === "LICENSE_REQUIRED"
                          ? "Cần cấp quyền"
                          : "Lỗi nguồn"}
                  </span>
                  <div>
                    <strong>{source.display_name}</strong>
                    <small>
                      {source.category} · {source.cadence} · {source.record_count} bản ghi
                    </small>
                    <p>
                      Dữ liệu quan sát: {dateTime(source.observed_at)}
                      {source.last_error ? ` · ${source.last_error}` : ""}
                    </p>
                  </div>
                  <a href={source.source_url} target="_blank" rel="noreferrer">
                    Mở nguồn ↗
                  </a>
                </article>
              ))}
            </div>
            <p className="data-disclaimer">
              Dữ liệu có độ trễ và chỉ phục vụ nghiên cứu/giáo dục. Các giả định lợi nhuận,
              biến động và rủi ro vẫn do mô hình tính toán.
            </p>
          </div>
        </div>
      )}

      {showDepositComparison && (
        <div className="modal-backdrop" onClick={() => setShowDepositComparison(false)}>
          <div
            className="audit-modal deposit-modal"
            onClick={(event) => event.stopPropagation()}
          >
            <div className="modal-title">
              <div>
                <span className="eyebrow">MBBank · Techcombank · VPBank</span>
                <h3>So sánh tiền gửi theo điều kiện thực tế</h3>
                <p>Chọn số vốn, kỳ hạn và phân khúc; hệ thống không tự gán ưu đãi.</p>
              </div>
              <button onClick={() => setShowDepositComparison(false)}>Đóng</button>
            </div>
            <form className="deposit-filters" onSubmit={compareDepositRates}>
              <NumberField
                label="Số vốn gửi"
                value={depositAmount}
                onChange={setDepositAmount}
              />
              <label className="field">
                <span>Kỳ hạn</span>
                <select
                  value={depositTenor}
                  onChange={(event) => setDepositTenor(Number(event.target.value))}
                >
                  {[1, 3, 6, 12, 18, 24, 36].map((value) => (
                    <option key={value} value={value}>{value} tháng</option>
                  ))}
                </select>
              </label>
              <label className="field">
                <span>Phân khúc khách hàng</span>
                <select
                  value={depositSegment}
                  onChange={(event) => setDepositSegment(event.target.value)}
                >
                  <option value="retail">Phổ thông</option>
                  <option value="priority">Ưu tiên</option>
                  <option value="private">Private</option>
                </select>
              </label>
              <button className="primary-action" disabled={depositLoading}>
                {depositLoading ? "Đang đối chiếu…" : "So sánh"}
              </button>
            </form>
            {depositResult ? (
              <>
                <p className="deposit-guidance">{depositResult.guidance}</p>
                <div className="deposit-grid">
                  {depositResult.comparisons.map((row) => (
                    <article
                      key={row.product_id}
                      className={row.eligible ? "eligible" : "ineligible"}
                    >
                      <div>
                        <strong>{row.provider}</strong>
                        <span>{row.eligible ? "ĐỦ ĐIỀU KIỆN" : "CHƯA ĐỦ ĐIỀU KIỆN"}</span>
                      </div>
                      <b>{pct(row.annual_rate)}<small>/năm</small></b>
                      <p>Lãi cuối kỳ <strong>{money.format(row.projected_interest)}</strong></p>
                      <p>Đáo hạn <strong>{money.format(row.maturity_amount)}</strong></p>
                      <small>{row.eligibility_reasons.join(" ")}</small>
                      <time>Cập nhật {dateTime(row.data_timestamp)}</time>
                    </article>
                  ))}
                </div>
                <p className="data-disclaimer">{depositResult.calculation_note}</p>
              </>
            ) : (
              <div className="deposit-empty">
                Nhấn “So sánh” để đối chiếu đúng kỳ hạn, số vốn và phân khúc.
              </div>
            )}
          </div>
        </div>
      )}
    </div>
  );
}

export default App;
