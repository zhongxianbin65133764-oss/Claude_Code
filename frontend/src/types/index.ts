export interface User {
  id: string;
  email: string;
  name: string;
  role: 'ADMIN' | 'MANAGER' | 'USER';
}

export interface Fund {
  id: string;
  name: string;
  code: string;
  type: 'VC' | 'PE' | 'GROWTH' | 'BUYOUT';
  totalSize: number;
  raisedAmount: number;
  currency: string;
  establishDate: string;
  duration: number;
  managementFee: number;
  carriedInterest: number;
  status: 'FUNDRAISING' | 'INVESTING' | 'MANAGEMENT' | 'EXIT' | 'LIQUIDATED';
  description?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Project {
  id: string;
  name: string;
  code: string;
  industry: string;
  stage: 'SEED' | 'ANGEL' | 'A_ROUND' | 'B_ROUND' | 'C_ROUND' | 'PRE_IPO' | 'GROWTH' | 'MATURE';
  region: string;
  description?: string;
  fundId: string;
  investmentAmount?: number;
  valuation?: number;
  shareholding?: number;
  investmentDate?: string;
  status: 'SOURCING' | 'SCREENING' | 'DUE_DILIGENCE' | 'DECISION' | 'INVESTED' | 'POST_INVESTMENT' | 'EXITING' | 'EXITED' | 'REJECTED';
  createdAt: string;
  updatedAt: string;
}

export interface Workflow {
  id: string;
  projectId: string;
  type: 'PROJECT_INITIATION' | 'INVESTMENT_DECISION' | 'POST_INVESTMENT' | 'EXIT_APPROVAL';
  status: 'PENDING' | 'APPROVED' | 'REJECTED' | 'CANCELLED';
  currentStep: number;
  totalSteps: number;
  initiator: string;
  description?: string;
  createdAt: string;
  updatedAt: string;
}

export interface Investor {
  id: string;
  name: string;
  type: 'INDIVIDUAL' | 'INSTITUTION' | 'GOVERNMENT';
  idNumber?: string;
  contactName: string;
  contactPhone: string;
  contactEmail: string;
  commitment: number;
  paidAmount: number;
  fundId: string;
  joinDate: string;
  status: string;
}
