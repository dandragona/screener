import { render, screen, fireEvent, waitFor, within } from '@testing-library/react'
import { describe, it, expect, vi, beforeEach } from 'vitest'
import App from './App'

// Mocking global fetch
global.fetch = vi.fn()

describe('App', () => {
    beforeEach(() => {
        vi.resetAllMocks()
    })

    it('renders and fetches data on mount', async () => {
        // Mock successful screen response
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [
                { symbol: 'AAPL', calculated_metrics: { score: 90 } },
                { symbol: 'GOOG', calculated_metrics: { score: 80 } }
            ],
        })

        render(<App />)
        // Expect header
        expect(screen.getByText('Arc Screener')).toBeInTheDocument()

        await waitFor(() => {
            expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/screen'))
            expect(screen.getByText('AAPL')).toBeInTheDocument()
            expect(screen.getByText('GOOG')).toBeInTheDocument()
        })
    })

    it('handles analysis caching', async () => {
        const mockTicker = {
            symbol: 'AAPL',
            current_price: 150,
            calculated_metrics: { score: 90 }
        }

        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [mockTicker],
        })

        render(<App />)

        await waitFor(() => {
            expect(screen.getByText('AAPL')).toBeInTheDocument()
        })

        // 1. Click Analyze -> API call
        const analyzeButton = screen.getByText('Analyze')
        const mockAnalysis = { symbol: 'AAPL', analysis: 'Good stock' }

        // Mock next fetch for analyze
        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockAnalysis,
        })

        fireEvent.click(analyzeButton)

        await waitFor(() => {
            expect(screen.getByText('Analysis: AAPL')).toBeInTheDocument()
        })

        // Verify call
        expect(fetch).toHaveBeenCalledTimes(2) // 1 for screen, 1 for analyze

        // Close modal
        fireEvent.click(screen.getByText('×'))

        // 2. Click Analyze again -> No API call (should use cache)
        fireEvent.click(analyzeButton)

        await waitFor(() => {
            expect(screen.getByText('Analysis: AAPL')).toBeInTheDocument()
        })

        // Still only 2 calls
        expect(fetch).toHaveBeenCalledTimes(2)
    })

    it('sorts data when column headers are clicked', async () => {
        // Mock data
        const mockData = [
            { symbol: 'AAA', current_price: 100, calculated_metrics: { score: 50 } },
            { symbol: 'BBB', current_price: 200, calculated_metrics: { score: 80 } },
            { symbol: 'CCC', current_price: 50, calculated_metrics: { score: 20 } }
        ]

        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => mockData,
        })

        render(<App />)

        await waitFor(() => {
            expect(screen.getByText('AAA')).toBeInTheDocument()
        })

        // Helper to get rows
        const getRows = () => screen.getAllByRole('row').slice(1) // skip header

        // Initial sort is Score desc
        // BBB (80), AAA (50), CCC (20)
        let rows = getRows()
        expect(within(rows[0]).getByText('BBB')).toBeInTheDocument()
        expect(within(rows[1]).getByText('AAA')).toBeInTheDocument()
        expect(within(rows[2]).getByText('CCC')).toBeInTheDocument()

        // 1. Sort by Price (click Header)
        const priceHeader = screen.getByText(/Price/)
        fireEvent.click(priceHeader)

        // Should be Price Desc (first click)
        // BBB (200), AAA (100), CCC (50)
        rows = getRows()
        expect(within(rows[0]).getByText('BBB')).toBeInTheDocument()
        expect(within(rows[1]).getByText('AAA')).toBeInTheDocument()
        expect(within(rows[2]).getByText('CCC')).toBeInTheDocument()

        // 2. Sort by Price again (asc)
        fireEvent.click(priceHeader)
        // Should be Price Asc
        // CCC (50), AAA (100), BBB (200)
        rows = getRows()
        expect(within(rows[0]).getByText('CCC')).toBeInTheDocument()
        expect(within(rows[1]).getByText('AAA')).toBeInTheDocument()
        expect(within(rows[2]).getByText('BBB')).toBeInTheDocument()

        // 3. Sort by Symbol
        const symbolHeader = screen.getByText(/Symbol/)
        fireEvent.click(symbolHeader)
        // Symbol Desc
        // CCC, BBB, AAA
        rows = getRows()
        expect(within(rows[0]).getByText('CCC')).toBeInTheDocument()
        expect(within(rows[1]).getByText('BBB')).toBeInTheDocument()
        expect(within(rows[2]).getByText('AAA')).toBeInTheDocument()

        // 4. Sort by Symbol Asc
        fireEvent.click(symbolHeader)
        // AAA, BBB, CCC
        rows = getRows()
        expect(within(rows[0]).getByText('AAA')).toBeInTheDocument()
        expect(within(rows[1]).getByText('BBB')).toBeInTheDocument()
        expect(within(rows[2]).getByText('CCC')).toBeInTheDocument()
    })
})
