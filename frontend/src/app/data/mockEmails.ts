import { Email } from '../types';

export const mockEmails: Email[] = [
  {
    id: 'email_001',
    sender: {
      name: 'Sarah Chen',
      email: 'sarah.chen@techcorp.com',
      avatar: 'https://images.unsplash.com/photo-1494790108377-be9c29b29330?auto=format&fit=crop&q=80&w=150',
    },
    subject: 'Q2 Product Roadmap Review - Urgent',
    preview: 'Hi team, I need everyone to review the attached Q2 roadmap by EOD...',
    body: `
      <p>Hi team,</p>
      <p>I need everyone to review the attached Q2 roadmap by EOD tomorrow. We have a board meeting on Friday and I want to make sure all departmental goals are aligned.</p>
      <p>Specifically, please check:</p>
      <ul>
        <li>Timeline feasibility</li>
        <li>Resource allocation</li>
        <li>Key deliverables</li>
      </ul>
      <p>Let me know if you see any major red flags.</p>
      <p>Best,<br>Sarah</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 30).toISOString(), // 30 mins ago
    read: false,
    folder: 'inbox',
    labels: ['Work', 'Q2 Planning'],
    aiAnalysis: {
      category: 'Urgent',
      sentiment: 'neutral',
      summary: 'Request for Q2 roadmap review by EOD tomorrow, focusing on timelines and resources.',
      suggestedActions: [
        'Draft response acknowledging receipt',
        'Schedule time to review roadmap',
        'Forward to engineering lead',
      ],
    },
  },
  {
    id: 'email_002',
    sender: {
      name: 'Alex Rivera',
      email: 'alex.rivera@designstudio.io',
      avatar: 'https://images.unsplash.com/photo-1507003211169-0a1dd7228f2d?auto=format&fit=crop&q=80&w=150',
    },
    subject: 'New Design Mockups for Dashboard',
    preview: 'Hey! Here are the updated mockups based on yesterday\'s feedback...',
    body: `
      <p>Hey!</p>
      <p>Here are the updated mockups based on yesterday's feedback. I've adjusted the color palette to be more accessible and cleaned up the navigation hierarchy.</p>
      <p>The Figma link is attached below. Let me know what you think!</p>
      <p>Cheers,<br>Alex</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 2).toISOString(), // 2 hours ago
    read: true,
    folder: 'inbox',
    labels: ['Design', 'Project X'],
    aiAnalysis: {
      category: 'Work',
      sentiment: 'positive',
      summary: 'Updated dashboard mockups with accessibility improvements ready for review.',
      suggestedActions: [
        'Open Figma link',
        'Reply with feedback',
        'Schedule design review meeting',
      ],
    },
  },
  {
    id: 'email_003',
    sender: {
      name: 'Stripe',
      email: 'notifications@stripe.com',
    },
    subject: 'Invoice #3492-01 payment successful',
    preview: 'Your payment of $29.00 for Pro Plan was successful.',
    body: `
      <p>Hi there,</p>
      <p>This is a confirmation that your payment of <strong>$29.00</strong> for the Pro Plan was successful.</p>
      <p>You can view your invoice and payment history in your dashboard.</p>
      <p>Thanks for your business!</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 5).toISOString(), // 5 hours ago
    read: false,
    folder: 'inbox',
    labels: ['Finance', 'Receipts'],
    aiAnalysis: {
      category: 'Finance',
      sentiment: 'neutral',
      summary: 'Payment confirmation for $29.00 Pro Plan subscription.',
      suggestedActions: [
        'Download invoice',
        'Archive email',
      ],
    },
  },
  {
    id: 'email_004',
    sender: {
      name: 'Mom',
      email: 'p.davis55@gmail.com',
    },
    subject: 'Weekend Plans?',
    preview: 'Are you coming home this weekend? Dad is making his famous lasagna...',
    body: `
      <p>Hi honey,</p>
      <p>Are you coming home this weekend? Dad is making his famous lasagna on Saturday night and we'd love to see you.</p>
      <p>Let me know so I can get the groceries!</p>
      <p>Love,<br>Mom</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 24).toISOString(), // 1 day ago
    read: true,
    folder: 'inbox',
    labels: ['Personal', 'Family'],
    aiAnalysis: {
      category: 'Personal',
      sentiment: 'positive',
      summary: 'Invitation to visit home this weekend for dinner.',
      suggestedActions: [
        'Reply "Yes, I\'ll be there"',
        'Reply "Sorry, I can\'t make it"',
        'Call Mom',
      ],
    },
  },
  {
    id: 'email_005',
    sender: {
      name: 'LinkedIn Job Alerts',
      email: 'jobs-listings@linkedin.com',
    },
    subject: '30+ new jobs match your preferences',
    preview: 'Senior Frontend Engineer at Google, UX Designer at Apple...',
    body: `
      <p>Here are the latest jobs matching your preferences:</p>
      <ul>
        <li><strong>Senior Frontend Engineer</strong> - Google</li>
        <li><strong>UX Designer</strong> - Apple</li>
        <li><strong>Product Manager</strong> - Linear</li>
      </ul>
      <p>Click to apply now.</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 48).toISOString(), // 2 days ago
    read: true,
    folder: 'inbox',
    labels: ['Social', 'Careers'],
    aiAnalysis: {
      category: 'Promotions',
      sentiment: 'neutral',
      summary: 'Job alert listing new opportunities at major tech companies.',
      suggestedActions: [
        'View all jobs',
        'Update job preferences',
        'Unsubscribe',
      ],
    },
  },
  {
    id: 'email_006',
    sender: {
      name: 'AWS Billing',
      email: 'no-reply-aws@amazon.com',
    },
    subject: 'AWS Budget Alert: Monthly Budget Exceeded',
    preview: 'Your account 123456789012 has exceeded your monthly budget of $100.00...',
    body: `
      <p>Hello,</p>
      <p>Your AWS account 123456789012 has exceeded your monthly budget of $100.00. The current forecast is $150.00.</p>
      <p>Please review your usage immediately to avoid unexpected charges.</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 3).toISOString(),
    read: false,
    folder: 'inbox',
    labels: ['Finance', 'Work'],
    aiAnalysis: {
      category: 'Urgent',
      sentiment: 'negative',
      summary: 'AWS budget alert: $100 limit exceeded, forecast $150.',
      suggestedActions: [
        'Log in to AWS Console',
        'Check EC2 instances',
        'Forward to DevOps',
      ],
    },
  },
    {
    id: 'email_007',
    sender: {
      name: 'David Kim',
      email: 'david.kim@startup.com',
    },
    subject: 'Re: Partnership Proposal',
    preview: 'Thanks for sending this over. We are interested but have a few questions...',
    body: `
      <p>Hi,</p>
      <p>Thanks for sending this over. We are interested in the partnership proposal but have a few questions about the revenue sharing model.</p>
      <p>Can we jump on a quick call next Tuesday to discuss?</p>
      <p>Best,<br>David</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 24 * 3).toISOString(),
    read: true,
    folder: 'sent',
    labels: ['Work', 'Partnership'],
    aiAnalysis: {
      category: 'Work',
      sentiment: 'positive',
      summary: 'Expressed interest in partnership, requested call next Tuesday to discuss revenue share.',
      suggestedActions: [
        'Schedule call',
        'Prepare revenue share details',
      ],
    },
  },
  {
    id: 'email_008',
    sender: {
      name: 'Draft: Marketing Team',
      email: 'marketing@techcorp.com',
    },
    subject: 'Q3 Marketing Strategy Brainstorm',
    preview: 'Hi everyone, I wanted to get a head start on Q3...',
    body: `
      <p>Hi everyone,</p>
      <p>I wanted to get a head start on Q3 marketing strategy. Here are some initial thoughts:</p>
      <ul>
        <li>Focus on organic growth</li>
        <li>Revamp the blog</li>
      </ul>
      <p>Let's discuss next week.</p>
    `,
    date: new Date(Date.now() - 1000 * 60 * 60 * 12).toISOString(),
    read: true,
    folder: 'drafts',
    labels: ['Work', 'Marketing', 'Strategy'],
    aiAnalysis: {
      category: 'Work',
      sentiment: 'neutral',
      summary: 'Draft email about Q3 marketing strategy brainstorming.',
      suggestedActions: [
        'Finish draft',
        'Discard draft',
      ],
    },
  },
];
