// Navigation items
export const navItems = [
  { label: 'Platform', href: '/platform' },
  { label: 'Architecture', href: '/architecture' },
  { label: 'Products', href: '/products' },
  { label: 'Solutions', href: '/solutions' },
  { label: 'Industries', href: '/industries' },
  { label: 'Pricing', href: '/pricing' },
  { label: 'About', href: '/about' },
];

// Footer links
export const footerLinks = {
  Product: [
    { label: 'Platform', href: '/platform' },
    { label: 'Architecture', href: '/architecture' },
    { label: 'Products', href: '/products' },
    { label: 'Solutions', href: '/solutions' },
    { label: 'Pricing', href: '/pricing' },
  ],
  Company: [
    { label: 'About', href: '/about' },
    { label: 'Partners', href: '/partners' },
    { label: 'Careers', href: '/careers' },
    { label: 'Contact', href: '/contact' },
  ],
  Resources: [
    { label: 'Blog', href: '/blog' },
    { label: 'FAQ', href: '/faq' },
    { label: 'Security', href: '/security' },
    { label: 'Documentation', href: '/platform' },
  ],
  Legal: [
    { label: 'Privacy', href: '/privacy' },
    { label: 'Terms', href: '/terms' },
    { label: 'Cookie Policy', href: '/cookie-policy' },
  ],
};

// Products data
export const products = [
  { name: 'DentalPilot AI', status: 'Live', icon: '🦷', desc: 'AI-powered dental marketing and practice management', color: 'from-blue-500 to-cyan-500' },
  { name: 'Fertility & IVF AI', status: 'Coming Soon', icon: '👶', desc: 'Intelligent fertility clinic management', color: 'from-pink-500 to-rose-500' },
  { name: 'Gynaecology AI', status: 'Coming Soon', icon: '🌸', desc: 'Comprehensive women\'s health platform', color: 'from-purple-500 to-pink-500' },
  { name: 'Aesthetic Dermatology AI', status: 'Coming Soon', icon: '✨', desc: 'Practice growth and patient engagement', color: 'from-orange-500 to-amber-500' },
  { name: 'Hair Transplant AI', status: 'Coming Soon', icon: '💇', desc: 'Specialized hair restoration workflows', color: 'from-amber-500 to-yellow-500' },
  { name: 'Ophthalmology AI', status: 'Coming Soon', icon: '👁️', desc: 'Eye care practice intelligence', color: 'from-emerald-500 to-teal-500' },
  { name: 'Plastic Surgery AI', status: 'Coming Soon', icon: '🔬', desc: 'Aesthetic and reconstructive workflows', color: 'from-indigo-500 to-purple-500' },
  { name: 'Cardiology AI', status: 'Coming Soon', icon: '❤️', desc: 'Heart health practice management', color: 'from-red-500 to-rose-500' },
  { name: 'Orthopaedics AI', status: 'Coming Soon', icon: '🦴', desc: 'Musculoskeletal care coordination', color: 'from-slate-500 to-gray-500' },
];

// Industries data
export const industries = [
  { name: 'Dental', icon: '🦷', count: 'Product Live', desc: 'Comprehensive dental practice management' },
  { name: 'Fertility & IVF', icon: '👶', count: 'Coming Soon', desc: 'Fertility clinic operations' },
  { name: 'Dermatology', icon: '✨', count: 'Coming Soon', desc: 'Skin health and aesthetics' },
  { name: 'Ophthalmology', icon: '👁️', count: 'Coming Soon', desc: 'Eye care and vision' },
  { name: 'Cardiology', icon: '❤️', count: 'Coming Soon', desc: 'Heart health management' },
  { name: 'Orthopaedics', icon: '🦴', count: 'Coming Soon', desc: 'Bone and joint care' },
  { name: 'Plastic Surgery', icon: '🔬', count: 'Coming Soon', desc: 'Aesthetic and reconstructive' },
  { name: 'General Practice', icon: '🩺', count: 'Planned', desc: 'Primary care coordination' },
  { name: 'Multi-Specialty', icon: '🏥', count: 'Planned', desc: 'Hospital networks' },
];

// Features data
export const features = [
  { icon: '🏥', title: 'Specialty Products', desc: 'Purpose-built AI solutions for dental, IVF, dermatology, and more. Each tailored to clinical workflows.' },
  { icon: '🔐', title: 'Enterprise Security', desc: 'HIPAA-compliant, SOC 2 certified. Your patient data is encrypted and protected at every layer.' },
  { icon: '🔗', title: 'Connected Ecosystem', desc: 'Seamless integration with existing EHR, PMS, and lab systems. No disruption to your workflow.' },
  { icon: '📊', title: 'Advanced Analytics', desc: 'Real-time insights into practice performance, patient outcomes, and operational efficiency.' },
  { icon: '🤖', title: 'AI-Powered', desc: 'Claude-powered intelligence for content generation, clinical notes, and patient communication.' },
  { icon: '🌍', title: 'Global Ready', desc: 'Multi-region deployment, data residency controls, and localization support out of the box.' },
];

// Platform features
export const platformFeatures = [
  { title: 'Multi-Tenant', icon: '🏢', desc: 'Complete tenant isolation with branch-level access control' },
  { title: 'Consent Management', icon: '✅', desc: 'Granular patient consent with audit trails' },
  { title: 'Communication', icon: '📧', desc: 'Email, SMS, WhatsApp with retry logic' },
  { title: 'Financial Engine', icon: '💰', desc: 'Billing, payments, insurance claims' },
  { title: 'Integration Hub', icon: '🔌', desc: 'CSV, API connectors for PMS/EHR' },
  { title: 'Analytics', icon: '📈', desc: 'Real-time practice intelligence' },
  { title: 'AI Governance', icon: '🤖', desc: 'Responsible AI with human oversight' },
  { title: 'Security', icon: '🔒', desc: 'HIPAA, SOC 2, encryption at rest' },
];

// Solutions data
export const solutions = [
  {
    title: 'Practice Management',
    desc: 'Streamline operations with intelligent scheduling, patient records, and billing automation.',
    features: ['Smart scheduling', 'Patient portal', 'Revenue cycle management', 'Insurance claims'],
    icon: '📊',
  },
  {
    title: 'Patient Engagement',
    desc: 'Build lasting relationships with personalized communication and care coordination.',
    features: ['Automated reminders', 'Patient education', 'Satisfaction surveys', 'Loyalty programs'],
    icon: '💬',
  },
  {
    title: 'Clinical Intelligence',
    desc: 'AI-powered insights to support clinical decision-making and improve outcomes.',
    features: ['Treatment planning', 'Risk stratification', 'Outcome tracking', 'Clinical research'],
    icon: '🧠',
  },
  {
    title: 'Growth & Marketing',
    desc: 'Attract and retain patients with data-driven marketing and reputation management.',
    features: ['Content generation', 'Social media automation', 'Review management', 'SEO optimization'],
    icon: '📈',
  },
];

// Pricing plans
export const pricingPlans = [
  {
    name: 'Starter',
    price: '$49',
    period: '/month',
    desc: 'For solo practitioners',
    features: ['1 provider', 'Up to 500 patients', 'AI content generation', 'Email support', 'Basic analytics'],
    cta: 'Start Starter',
    popular: false,
  },
  {
    name: 'Professional',
    price: '$149',
    period: '/month',
    desc: 'For growing practices',
    features: ['Up to 5 providers', 'Unlimited patients', 'Advanced analytics', 'Priority support', 'Custom integrations', 'Patient portal'],
    cta: 'Start Professional',
    popular: true,
  },
  {
    name: 'Enterprise',
    price: 'Custom',
    period: '',
    desc: 'For multi-location groups',
    features: ['Unlimited providers', 'Multi-location', 'Dedicated account manager', 'Custom development', 'SLA guarantee', 'On-premise options'],
    cta: 'Contact Sales',
    popular: false,
  },
];

// FAQ data
export const faqs = [
  { q: 'What is Otheryn?', a: 'Otheryn is a comprehensive healthcare platform that provides AI-powered tools and infrastructure for healthcare providers. We start with specialty-specific products like DentalPilot AI and expand across multiple healthcare domains.' },
  { q: 'Is Otheryn HIPAA compliant?', a: 'Yes, Otheryn is fully HIPAA compliant. We implement industry-standard security controls including encryption at rest and in transit, access controls, audit logs, and regular security assessments.' },
  { q: 'What specialties do you support?', a: 'We currently offer DentalPilot AI for dental practices. We are actively developing products for Fertility & IVF, Dermatology, Ophthalmology, Cardiology, Orthopaedics, Plastic Surgery, and more.' },
  { q: 'Can I integrate with my existing systems?', a: 'Yes, Otheryn provides integration capabilities with popular EHR/EMR systems, practice management software, and other healthcare tools through our API and CSV import/export features.' },
  { q: 'How does pricing work?', a: 'We offer tiered pricing starting at $49/month for solo practitioners. Professional plans start at $149/month for growing practices. Enterprise solutions are custom-priced for multi-location organizations.' },
  { q: 'Is there a free trial?', a: 'We do not offer a free trial. Paid plans include a 14-day money-back guarantee and can be cancelled anytime.' },
  { q: 'What kind of support do you offer?', a: 'We provide email support for all plans, priority support for Professional plans, and dedicated account management for Enterprise customers.' },
  { q: 'Where is my data stored?', a: 'Your data is stored in secure cloud infrastructure with options for US-based or EU-based data residency. All data is encrypted at rest using AES-256.' },
];

// Blog posts
export const blogPosts = [
  { title: 'The Future of AI in Healthcare', category: 'AI & Innovation', date: 'Nov 15, 2024', excerpt: 'How artificial intelligence is transforming patient care and practice operations.' },
  { title: 'Building a Connected Healthcare Ecosystem', category: 'Platform', date: 'Nov 10, 2024', excerpt: 'The importance of interoperability in modern healthcare.' },
  { title: 'Patient Privacy in the Digital Age', category: 'Security', date: 'Nov 5, 2024', excerpt: 'Best practices for protecting patient data in cloud environments.' },
];

// Security features
export const securityFeatures = [
  { title: 'HIPAA Compliant', icon: '🏥', desc: 'Full compliance with healthcare data protection regulations' },
  { title: 'SOC 2 Type II', icon: '🔒', desc: 'Independently audited security controls' },
  { title: 'Encryption', icon: '🛡️', desc: 'AES-256 at rest, TLS 1.3 in transit' },
  { title: 'Access Control', icon: '🔑', desc: 'Role-based access with audit trails' },
  { title: 'Data Residency', icon: '🌍', desc: 'Choose where your data is stored' },
  { title: 'Compliance', icon: '✅', desc: 'GDPR, CCPA, and more' },
];