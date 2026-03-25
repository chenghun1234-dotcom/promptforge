export default {
	content: ['./src/**/*.{astro,html,js,jsx,md,mdx,svelte,ts,tsx,vue}'],
	theme: {
		extend: {
			animation: {
				'text-glow': 'textGlow 3s ease-in-out infinite alternate',
				float: 'floating 3s ease-in-out infinite',
			},
			keyframes: {
				textGlow: {
					'0%': { textShadow: '0 0 10px #4ade80, 0 0 20px #4ade80' },
					'100%': { textShadow: '0 0 20px #22d3ee, 0 0 40px #22d3ee' },
				},
				floating: {
					'0%, 100%': { transform: 'translateY(0)' },
					'50%': { transform: 'translateY(-10px)' },
				},
			},
		},
	},
	plugins: [],
};
