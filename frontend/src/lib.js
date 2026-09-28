// Shared domain helpers: tiers, colours, labels.

export const FCI_THRESHOLDS = { high: 80, moderate: 50 };

export function fciTier(fci) {
  if (fci >= FCI_THRESHOLDS.high)
    return {
      key: 'high',
      label: 'HIGH CONFIDENCE',
      longLabel: 'HIGH CONFIDENCE — RELIABLE FOR OPERATIONS',
      color: '#15803d',
      bg: '#dcfce7',
      border: '#86d6a0',
    };
  if (fci >= FCI_THRESHOLDS.moderate)
    return {
      key: 'moderate',
      label: 'MODERATE',
      longLabel: 'MODERATE CONFIDENCE — MONITOR ENSEMBLES',
      color: '#b45309',
      bg: '#fef3c7',
      border: '#f2cf7f',
    };
  return {
    key: 'low',
    label: 'BUST ALERT',
    longLabel: 'BUST ALERT — HIGH RISK OF LARGE ERROR',
    color: '#b91c1c',
    bg: '#fee2e2',
    border: '#f3a3a3',
  };
}

export function bustColor(p) {
  if (p >= 0.6) return '#dc2626';
  if (p >= 0.3) return '#d97706';
  return '#15803d';
}

export function rainColor(mm) {
  if (mm >= 64.5) return '#0b3d6b';
  if (mm >= 15.5) return '#0e7fc4';
  return '#9ecfe8';
}

export const LAYERS = {
  fci: { label: 'Confidence Index', short: 'FCI', unit: 'FCI %' },
  prob: { label: 'Bust Probability', short: 'P(Bust)', unit: 'Risk' },
  rain: { label: 'NWP Precipitation', short: 'Rain', unit: 'mm/day' },
};

export const FALLBACK_DATES = [
  '2019-07-15',
  '2019-07-16',
  '2019-07-17',
  '2019-07-18',
  '2019-07-19',
];

export const pct1 = (x) => `${(Number(x) * 100).toFixed(1)}%`;
export const fci1 = (x) => `${Number(x).toFixed(1)}%`;

export function advisoryFor(region, leadDay) {
  const name = region.subdivision_name;
  const p = pct1(region.bust_probability);
  if (region.confidence_index >= 80)
    return `NWP guidance for ${name} (Day ${leadDay}) is consistent with historical error behaviour. Routine IMD/NCMRWF protocol applies; no special bust precautions beyond standard verification.`;
  if (region.confidence_index >= 50)
    return `Elevated uncertainty over ${name} (Day ${leadDay}). Cross-check ensemble spread, delay high-stakes decisions (evacuation/advisory escalation) and re-verify at the next 00/12 UTC cycle.`;
  return `BUST ALERT: Do NOT rely on single deterministic rainfall guidance for ${name} (Day ${leadDay}). High bust probability (${p}). Activate contingency review, consult ensemble distribution and nowcast inputs before public advisory.`;
}

export const SUBDIVISION_CITIES = {
  KONKAN_GOA: ['Mumbai', 'Panaji', 'Ratnagiri', 'Thane'],
  COASTAL_KARNATAKA: ['Mangaluru', 'Udupi', 'Karwar', 'Bhatkal'],
  SAURASHTRA_KUTCH: ['Rajkot', 'Bhuj', 'Jamnagar', 'Porbandar'],
  GUJARAT_REGION: ['Ahmedabad', 'Surat', 'Vadodara', 'Gandhinagar'],
  ODISHA: ['Bhubaneswar', 'Cuttack', 'Puri', 'Balasore', 'Rourkela'],
  GANGETIC_WB: ['Kolkata', 'Howrah', 'Asansol', 'Durgapur', 'Haldia'],
  VIDARBHA: ['Nagpur', 'Amravati', 'Akola', 'Chandrapur'],
  MARATHWADA: ['Chhatrapati Sambhajinagar', 'Nanded', 'Latur', 'Jalna'],
  EAST_MP: ['Jabalpur', 'Rewa', 'Sagar', 'Satna', 'Singrauli'],
  WEST_MP: ['Bhopal', 'Indore', 'Ujjain', 'Gwalior'],
  EAST_RAJASTHAN: ['Jaipur', 'Kota', 'Ajmer', 'Udaipur', 'Bhilwara'],
  WEST_RAJASTHAN: ['Jodhpur', 'Bikaner', 'Jaisalmer', 'Barmer'],
  HARYANA_DELHI: ['New Delhi', 'Gurugram', 'Chandigarh', 'Faridabad', 'Ambala'],
  WEST_UP: ['Noida', 'Meerut', 'Agra', 'Bareilly', 'Aligarh'],
  EAST_UP: ['Lucknow', 'Varanasi', 'Prayagraj', 'Gorakhpur', 'Kanpur'],
  TELANGANA: ['Hyderabad', 'Warangal', 'Nizamabad', 'Karimnagar'],
  COASTAL_ANDHRA: ['Visakhapatnam', 'Vijayawada', 'Guntur', 'Kakinada', 'Nellore'],
  KERALA: ['Thiruvananthapuram', 'Kochi', 'Kozhikode', 'Thrissur', 'Kannur'],
  MADHYA_MAHARASHTRA: ['Pune', 'Nashik', 'Kolhapur', 'Satara'],
  CHHATTISGARH: ['Raipur', 'Bilaspur', 'Durg', 'Korba'],
  JHARKHAND: ['Ranchi', 'Jamshedpur', 'Dhanbad', 'Bokaro'],
  BIHAR: ['Patna', 'Gaya', 'Muzaffarpur', 'Bhagalpur'],
  UTTARAKHAND: ['Dehradun', 'Haridwar', 'Haldwani', 'Rishikesh'],
  PUNJAB: ['Ludhiana', 'Amritsar', 'Jalandhar', 'Patiala'],
  HIMACHAL: ['Shimla', 'Mandi', 'Dharamshala', 'Solan'],
  JAMMU_KASHMIR_LADAKH: ['Srinagar', 'Jammu', 'Leh', 'Anantnag'],
  RAYALASEEMA: ['Tirupati', 'Anantapur', 'Kurnool', 'Kadapa'],
  TAMIL_NADU: ['Chennai', 'Coimbatore', 'Madurai', 'Tiruchirappalli', 'Salem'],
  NORTH_KARNATAKA: ['Hubballi', 'Belagavi', 'Kalaburagi', 'Vijayapura'],
  SOUTH_KARNATAKA: ['Bengaluru', 'Mysuru', 'Shivamogga', 'Ballari'],
  ASSAM_MEGHALAYA: ['Guwahati', 'Shillong', 'Dibrugarh', 'Silchar'],
  ARUNACHAL: ['Itanagar', 'Tawang', 'Ziro', 'Pasighat'],
  NMMT: ['Kohima', 'Imphal', 'Aizawl', 'Agartala'],
  SHWB_SIKKIM: ['Siliguri', 'Gangtok', 'Darjeeling', 'Jalpaiguri'],
  ANDAMAN_NICOBAR: ['Port Blair', 'Car Nicobar', 'Mayabunder'],
  LAKSHADWEEP: ['Kavaratti', 'Agatti', 'Minicoy'],
};
