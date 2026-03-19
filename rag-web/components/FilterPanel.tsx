'use client';

import { useState, useEffect } from 'react';
import { api, type AvailableFilters } from '@/lib/api';

interface FilterPanelProps {
    onFiltersChange: (filters: Record<string, any>) => void;
    activeFilters: Record<string, any>;
}

export default function FilterPanel({ onFiltersChange, activeFilters }: FilterPanelProps) {
    const [availableFilters, setAvailableFilters] = useState<AvailableFilters | null>(null);
    const [loading, setLoading] = useState(true);
    const [expanded, setExpanded] = useState(false);
    const [localFilters, setLocalFilters] = useState<Record<string, any>>(activeFilters);

    useEffect(() => {
        loadAvailableFilters();
    }, []);

    useEffect(() => {
        setLocalFilters(activeFilters);
    }, [activeFilters]);

    const loadAvailableFilters = async () => {
        try {
            const filters = await api.getAvailableFilters();
            setAvailableFilters(filters);
        } catch (error) {
            console.error('Failed to load filters:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleFilterChange = (field: string, value: any) => {
        const newFilters = { ...localFilters };
        
        if (value === '' || value === null || (Array.isArray(value) && value.length === 0)) {
            delete newFilters[field];
        } else {
            newFilters[field] = value;
        }
        
        setLocalFilters(newFilters);
        onFiltersChange(newFilters);
    };

    const handleComplianceTagToggle = (tag: string) => {
        const currentTags = localFilters.compliance_tags || [];
        const newTags = currentTags.includes(tag)
            ? currentTags.filter((t: string) => t !== tag)
            : [...currentTags, tag];
        
        handleFilterChange('compliance_tags', newTags.length > 0 ? newTags : null);
    };

    const clearAllFilters = () => {
        setLocalFilters({});
        onFiltersChange({});
    };

    const activeFilterCount = Object.keys(localFilters).length;

    if (loading) {
        return (
            <div className="p-4 bg-gray-50 border border-gray-200 rounded-lg">
                <p className="text-sm text-gray-500">Loading filters...</p>
            </div>
        );
    }

    if (!availableFilters) {
        return null;
    }

    return (
        <div className="bg-gradient-to-r from-blue-50 to-purple-50 border border-blue-200 rounded-lg overflow-hidden">
            {/* Header */}
            <button
                onClick={() => setExpanded(!expanded)}
                className="w-full px-4 py-3 flex items-center justify-between hover:bg-white/50 transition-colors"
            >
                <div className="flex items-center gap-2">
                    <span className="text-lg">🔍</span>
                    <span className="font-semibold text-gray-800">Advanced Filters</span>
                    {activeFilterCount > 0 && (
                        <span className="px-2 py-0.5 bg-blue-600 text-white text-xs rounded-full">
                            {activeFilterCount}
                        </span>
                    )}
                </div>
                <span className={`transform transition-transform ${expanded ? 'rotate-180' : ''}`}>
                    ▼
                </span>
            </button>

            {/* Filter Content */}
            {expanded && (
                <div className="px-4 pb-4 space-y-3 border-t border-blue-200 pt-3 bg-white/30">
                    {/* Control Owner */}
                    {availableFilters.control_owner.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Control Owner
                            </label>
                            <select
                                value={localFilters.control_owner || ''}
                                onChange={(e) => handleFilterChange('control_owner', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                            >
                                <option value="">All Owners</option>
                                {availableFilters.control_owner.map((owner) => (
                                    <option key={owner} value={owner}>
                                        {owner}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Priority */}
                    {availableFilters.priority.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Priority Level
                            </label>
                            <div className="flex gap-2 flex-wrap">
                                {availableFilters.priority.map((priority) => (
                                    <button
                                        key={priority}
                                        onClick={() => handleFilterChange('priority', localFilters.priority === priority ? null : priority)}
                                        className={`px-3 py-1.5 text-sm rounded-md border transition-colors ${
                                            localFilters.priority === priority
                                                ? priority === 'Critical'
                                                    ? 'bg-red-600 text-white border-red-600'
                                                    : priority === 'High'
                                                    ? 'bg-orange-500 text-white border-orange-500'
                                                    : priority === 'Medium'
                                                    ? 'bg-yellow-500 text-white border-yellow-500'
                                                    : 'bg-green-500 text-white border-green-500'
                                                : 'bg-white text-gray-700 border-gray-300 hover:border-blue-400'
                                        }`}
                                    >
                                        {priority}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Compliance Tags */}
                    {availableFilters.compliance_tags.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Compliance Tags ({(localFilters.compliance_tags || []).length} selected)
                            </label>
                            <div className="flex gap-2 flex-wrap max-h-32 overflow-y-auto p-2 bg-white rounded border border-gray-200">
                                {availableFilters.compliance_tags.map((tag) => (
                                    <button
                                        key={tag}
                                        onClick={() => handleComplianceTagToggle(tag)}
                                        className={`px-2.5 py-1 text-xs rounded-full border transition-colors ${
                                            (localFilters.compliance_tags || []).includes(tag)
                                                ? 'bg-blue-600 text-white border-blue-600'
                                                : 'bg-white text-gray-600 border-gray-300 hover:border-blue-400'
                                        }`}
                                    >
                                        {tag}
                                    </button>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Applies To */}
                    {availableFilters.applies_to.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Applies To
                            </label>
                            <select
                                value={localFilters.applies_to || ''}
                                onChange={(e) => handleFilterChange('applies_to', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                            >
                                <option value="">All Departments</option>
                                {availableFilters.applies_to.map((dept) => (
                                    <option key={dept} value={dept}>
                                        {dept}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Group */}
                    {availableFilters.group.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Procedure Group
                            </label>
                            <select
                                value={localFilters.group || ''}
                                onChange={(e) => handleFilterChange('group', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                            >
                                <option value="">All Groups</option>
                                {availableFilters.group.map((grp) => (
                                    <option key={grp} value={grp}>
                                        {grp}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Section ID */}
                    {availableFilters.section_id.length > 0 && (
                        <div>
                            <label className="block text-sm font-medium text-gray-700 mb-1">
                                Section
                            </label>
                            <select
                                value={localFilters.section_id || ''}
                                onChange={(e) => handleFilterChange('section_id', e.target.value)}
                                className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 bg-white"
                            >
                                <option value="">All Sections</option>
                                {availableFilters.section_id.map((section) => (
                                    <option key={section} value={section}>
                                        Section {section}
                                    </option>
                                ))}
                            </select>
                        </div>
                    )}

                    {/* Clear Filters Button */}
                    {activeFilterCount > 0 && (
                        <button
                            onClick={clearAllFilters}
                            className="w-full mt-2 px-4 py-2 bg-red-100 text-red-700 rounded-md hover:bg-red-200 transition-colors font-medium text-sm"
                        >
                            Clear All Filters ({activeFilterCount})
                        </button>
                    )}
                </div>
            )}
        </div>
    );
}
