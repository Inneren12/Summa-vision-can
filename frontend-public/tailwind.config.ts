import type { Config } from 'tailwindcss';

const config: Config = {
  content: ['./src/**/*.{ts,tsx,mdx}'],
  theme: {
    extend: {
      colors: {
        // Semantic UI
        'bg-app': 'var(--bg-app)',
        'bg-surface': 'var(--bg-surface)',
        'bg-surface-hover': 'var(--bg-surface-hover)',
        'bg-surface-active': 'var(--bg-surface-active)',
        'border-default': 'var(--border-default)',
        'border-subtle': 'var(--border-subtle)',
        'border-focus': 'var(--border-focus)',
        'text-primary': 'var(--text-primary)',
        'text-secondary': 'var(--text-secondary)',
        'text-muted': 'var(--text-muted)',
        'text-inverse': 'var(--text-inverse)',
        accent: 'var(--accent)',
        'accent-hover': 'var(--accent-hover)',
        'accent-muted': 'var(--accent-muted)',
        destructive: 'var(--destructive)',
        // Data Semantic
        'data-gov': 'var(--data-gov)',
        'data-society': 'var(--data-society)',
        'data-infra': 'var(--data-infra)',
        'data-monopoly': 'var(--data-monopoly)',
        'data-baseline': 'var(--data-baseline)',
        'data-housing': 'var(--data-housing)',
        'data-negative': 'var(--data-negative)',
        'data-positive': 'var(--data-positive)',
        'data-warning': 'var(--data-warning)',
        'data-neutral': 'var(--data-neutral)',
        // Component
        'card-bg': 'var(--card-bg)',
        'card-border': 'var(--card-border)',
        'tooltip-bg': 'var(--tooltip-bg)',
        'tooltip-text': 'var(--tooltip-text)',
        'btn-primary-bg': 'var(--btn-primary-bg)',
        'btn-primary-text': 'var(--btn-primary-text)',
      },
      fontFamily: {
        display: ['var(--font-display)'],
        body: ['var(--font-body)'],
        data: ['var(--font-data)'],
      },
      spacing: {
        'xs': 'var(--space-xs)',
        'sm': 'var(--space-sm)',
        'md': 'var(--space-md)',
        'lg': 'var(--space-lg)',
        'xl': 'var(--space-xl)',
        '2xl': 'var(--space-2xl)',
        '3xl': 'var(--space-3xl)',
      },
      borderRadius: {
        admin: 'var(--radius-admin)',
        public: 'var(--radius-public)',
        button: 'var(--radius-button)',
        tooltip: 'var(--radius-tooltip)',
      },
      boxShadow: {
        card: 'var(--shadow-card)',
        tooltip: 'var(--shadow-tooltip)',
        elevated: 'var(--shadow-elevated)',
      },
      zIndex: {
        base: 'var(--z-base)',
        sticky: 'var(--z-sticky)',
        'chart-overlay': 'var(--z-chart-overlay)',
        popover: 'var(--z-popover)',
        tooltip: 'var(--z-tooltip)',
        modal: 'var(--z-modal)',
        alert: 'var(--z-alert)',
      },
      transitionTimingFunction: {
        'ease-out-custom': 'var(--ease-out)',
      },
      transitionDuration: {
        micro: 'var(--duration-micro)',
        data: 'var(--duration-data)',
        page: 'var(--duration-page)',
      },
    },
  },
  plugins: [],
};

export default config;
