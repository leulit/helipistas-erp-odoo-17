/** @odoo-module **/

import { SearchPage } from "./search_page";
import { getFixture, mount, nextTick } from "@web/../tests/helpers/utils";
import { makeTestEnv } from "@web/../tests/helpers/mock_env";
import { registry } from "@web/core/registry";
import { hotkeyService } from "@web/core/hotkeys/hotkey_service";
import { uiService } from "@web/core/ui/ui_service";
import { actionService } from "@web/webclient/actions/action_service";

// Mock fetch for testing
const originalFetch = window.fetch;

// Test cases
QUnit.module("AI Universal Search", (hooks) => {
    let fixture;
    let env;
    let mockRPC;
    let searchPageComponent;
    
    // Setup before each test
    hooks.beforeEach(async () => {
        fixture = getFixture();
        
        // Set up service registry
        registry.category("services").add("hotkey", hotkeyService);
        registry.category("services").add("ui", uiService);
        registry.category("services").add("action", actionService);
        
        // Mock RPC
        mockRPC = (route, args) => {
            if (route === '/leulit_ai/search') {
                // Return mock data based on the query
                const query = args.params.query_text;
                if (query.toLowerCase().includes("listaa käyttäjät")) {
                    return Promise.resolve({
                        jsonrpc: "2.0",
                        id: args.id,
                        result: {
                            status: 'success',
                            result: {
                                model: 'res.users',
                                count: 2,
                                fields: ['id', 'name', 'login', 'email'],
                                records: [
                                    {id: 1, name: 'Admin', login: 'admin', email: 'admin@example.com'},
                                    {id: 2, name: 'Demo User', login: 'demo', email: 'demo@example.com'}
                                ]
                            }
                        }
                    });
                } else if (query.toLowerCase().includes("yhdistä sisäänkirjautumiset")) {
                    return Promise.resolve({
                        jsonrpc: "2.0",
                        id: args.id,
                        result: {
                            status: 'success',
                            result: {
                                multi_model: true,
                                total_count: 3,
                                results: [
                                    {
                                        model: 'res.users.log',
                                        model_label: 'User Logs',
                                        fields: ['id', 'create_date', 'create_uid'],
                                        records: [
                                            {
                                                id: 1, 
                                                create_date: '2025-03-15 10:00:00', 
                                                create_uid: [1, 'Admin'],
                                                user_info: {
                                                    id: 1,
                                                    name: 'Admin',
                                                    login: 'admin'
                                                }
                                            },
                                            {
                                                id: 2, 
                                                create_date: '2025-03-15 11:30:00', 
                                                create_uid: [2, 'Demo User'],
                                                user_info: {
                                                    id: 2,
                                                    name: 'Demo User',
                                                    login: 'demo'
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        model: 'res.users',
                                        model_label: 'Users',
                                        fields: ['id', 'name', 'login'],
                                        records: [
                                            {id: 1, name: 'Admin', login: 'admin'},
                                        ]
                                    }
                                ]
                            }
                        }
                    });
                }
            }
            return Promise.resolve(false);
        };
        
        // Create test environment
        env = await makeTestEnv({ mockRPC });
        
        // Mount the search page component
        searchPageComponent = await mount(SearchPage, fixture, { env });
    });
    
    // Cleanup after each test
    hooks.afterEach(() => {
        fixture.remove();
        window.fetch = originalFetch;
    });
    
    // Test for simple user list search functionality
    QUnit.test("Users list search renders correctly", async (assert) => {
        // Mock fetch response for the 'listaa käyttäjät' query
        window.fetch = async (url, options) => {
            if (url === '/leulit_ai/search') {
                const params = JSON.parse(options.body);
                const query = params.params.query_text;
                
                if (query === 'listaa käyttäjät') {
                    return {
                        ok: true,
                        json: () => Promise.resolve({
                            jsonrpc: "2.0",
                            id: params.id,
                            result: {
                                model: 'res.users',
                                count: 2,
                                fields: ['id', 'name', 'login', 'email'],
                                records: [
                                    {id: 1, name: 'Admin', login: 'admin', email: 'admin@example.com'},
                                    {id: 2, name: 'Demo User', login: 'demo', email: 'demo@example.com'}
                                ]
                            }
                        })
                    };
                }
            }
            return originalFetch(url, options);
        };
        
        // Set query and search
        searchPageComponent.state.query = 'listaa käyttäjät';
        await searchPageComponent.onSearch();
        await nextTick();
        
        // Check if results are processed correctly
        assert.ok(searchPageComponent.state.results, "Results should be available");
        assert.equal(searchPageComponent.state.results.model, 'res.users', "Model should be res.users");
        assert.equal(searchPageComponent.state.results.count, 2, "Should find 2 users");
        assert.equal(searchPageComponent.state.results.records.length, 2, "Should have 2 records");
        
        // Verify structure for frontend rendering
        assert.notOk(searchPageComponent.state.results.multi_model, "Should not be a multi-model result");
        assert.ok(searchPageComponent.state.results.fields, "Fields array should be present");
        assert.ok(searchPageComponent.state.results.records, "Records array should be present");
    });
    
    // Test for cross-model search functionality
    QUnit.test("Cross-model search renders correctly", async (assert) => {
        // Mock fetch response for the cross-model query
        window.fetch = async (url, options) => {
            if (url === '/leulit_ai/search') {
                const params = JSON.parse(options.body);
                const query = params.params.query_text;
                
                if (query === 'yhdistä sisäänkirjautumiset käyttäjän tietoihin') {
                    return {
                        ok: true,
                        json: () => Promise.resolve({
                            jsonrpc: "2.0",
                            id: params.id,
                            result: {
                                multi_model: true,
                                total_count: 3,
                                results: [
                                    {
                                        model: 'res.users.log',
                                        model_label: 'User Logs',
                                        fields: ['id', 'create_date', 'create_uid'],
                                        records: [
                                            {
                                                id: 1, 
                                                create_date: '2025-03-15 10:00:00', 
                                                create_uid: [1, 'Admin'],
                                                user_info: {
                                                    id: 1,
                                                    name: 'Admin',
                                                    login: 'admin'
                                                }
                                            }
                                        ]
                                    },
                                    {
                                        model: 'res.users',
                                        model_label: 'Users',
                                        fields: ['id', 'name', 'login'],
                                        records: [
                                            {id: 1, name: 'Admin', login: 'admin'},
                                        ]
                                    }
                                ]
                            }
                        })
                    };
                }
            }
            return originalFetch(url, options);
        };
        
        // Set query and search
        searchPageComponent.state.query = 'yhdistä sisäänkirjautumiset käyttäjän tietoihin';
        await searchPageComponent.onSearch();
        await nextTick();
        
        // Check if results are processed correctly
        assert.ok(searchPageComponent.state.results, "Results should be available");
        assert.ok(searchPageComponent.state.results.multi_model, "Should be a multi-model result");
        assert.equal(searchPageComponent.state.results.total_count, 3, "Total count should be 3");
        assert.equal(searchPageComponent.state.results.results.length, 2, "Should have 2 models");
        
        // Check logs model
        const logsModel = searchPageComponent.state.results.results.find(m => m.model === 'res.users.log');
        assert.ok(logsModel, "Logs model should be present");
        assert.equal(logsModel.records.length, 1, "Should have 1 log record");
        assert.ok(logsModel.records[0].user_info, "User info should be included");
        
        // Check users model
        const usersModel = searchPageComponent.state.results.results.find(m => m.model === 'res.users');
        assert.ok(usersModel, "Users model should be present");
        assert.equal(usersModel.records.length, 1, "Should have 1 user record");
    });
});
