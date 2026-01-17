import { render, screen, fireEvent, waitFor } from '@testing-library/react'
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
            json: async () => [],
        })

        render(<App />)
        expect(screen.getByText('AVG LEAPs')).toBeInTheDocument()

        await waitFor(() => {
            expect(fetch).toHaveBeenCalledWith(expect.stringContaining('/screen'))
        })
    })

    it('uses cached data if valid', async () => {
        // Setup valid cache
        const mockData = [{ symbol: 'AAPL', current_price: 150 }]
        const validCache = {
            data: mockData,
            timestamp: Date.now()
        }
        localStorage.setItem('screenerResults', JSON.stringify(validCache))

        render(<App />)

        // Should receive data from cache without fetch
        await waitFor(() => {
            expect(screen.getByText('AAPL')).toBeInTheDocument()
        })
        expect(fetch).not.toHaveBeenCalled()
    })

    it('fetches new data if cache is expired', async () => {
        // Setup expired cache (> 24h old)
        const mockData = [{ symbol: 'AAPL', current_price: 150 }]
        const expiredCache = {
            data: mockData,
            timestamp: Date.now() - (25 * 60 * 60 * 1000) // 25 hours ago
        }
        localStorage.setItem('screenerResults', JSON.stringify(expiredCache))

        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [{ symbol: 'GOOG', current_price: 200 }],
        })

        render(<App />)

        // Should verify fresh data loaded
        await waitFor(() => {
            expect(screen.getByText('GOOG')).toBeInTheDocument()
        })
        expect(fetch).toHaveBeenCalled()
    })

    it('refreshes data when refresh button is clicked', async () => {
        // Setup valid cache
        const mockData = [{ symbol: 'AAPL', current_price: 150 }]
        const validCache = {
            data: mockData,
            timestamp: Date.now()
        }
        localStorage.setItem('screenerResults', JSON.stringify(validCache))

        fetch.mockResolvedValueOnce({
            ok: true,
            json: async () => [{ symbol: 'MSFT', current_price: 300 }],
        })

        render(<App />)

        // Confirm initial load from cache
        await waitFor(() => {
            expect(screen.getByText('AAPL')).toBeInTheDocument()
        })
        expect(fetch).not.toHaveBeenCalled()

        // Click refresh
        const refreshButton = screen.getByText('Refresh Data')
        fireEvent.click(refreshButton)

        // Should fetch new data
        await waitFor(() => {
            expect(screen.getByText('MSFT')).toBeInTheDocument()
        })
        expect(fetch).toHaveBeenCalled()
    })

    it('handles analysis caching', async () => {
        // Mock initial screen load with no cache
        localStorage.clear()
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
        const analyzeButton = screen.getAllByText('Analyze')[0]
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

        // 2. Click Analyze again -> No API call
        fireEvent.click(analyzeButton)

        await waitFor(() => {
            expect(screen.getByText('Analysis: AAPL')).toBeInTheDocument()
        })

        // Still only 2 calls
        expect(fetch).toHaveBeenCalledTimes(2)
    })
})
