local function on_completion_result(context, err, _, result, prefix)
    if err or not result then
        return
    end

    local matches = vim.lsp.util.text_document_completion_list_to_complete_items(result, prefix)
    vim.api.nvim_call_function('ncm2#complete', {context, context.startccol, matches})
end

local function on_complete_lsp(context)
    -- adapted version of lsp.omnifunc function from neovim repo
    -- https://github.com/neovim/neovim/blob/master/runtime/lua/vim/lsp.lua

    local pos = vim.api.nvim_win_get_cursor(0)
    local line = vim.api.nvim_get_current_line()
    local line_to_cursor = line:sub(1, pos[2])
    local textMatch = vim.fn.match(line_to_cursor, '\\k*$')
    local prefix = line_to_cursor:sub(textMatch+1)

    vim.lsp.buf_request(
        context.bufnr,
        'textDocument/completion',
        vim.lsp.util.make_position_params(),
        function(err, _, result)
            on_completion_result(context, err, _, result, prefix)
        end
    )
end

local function escape(chars)
    local result = {}
    for i = 1, #chars do
        result[i] = vim.pesc(chars[i]):gsub('%%', '\\')
    end
    return result
end

local function register_lsp_source(client, result)
    if not client.server_capabilities.completionProvider then
        return
    end

    local bufnr = vim.api.nvim_get_current_buf()
    local filetype = vim.api.nvim_buf_get_option(bufnr, 'filetype')
    local trigger_chars = client
        .server_capabilities
        .completionProvider
        .triggerCharacters
        or {}
    local source = {
        name = 'nlc_' .. filetype,
        priority = 9,
        scope = {filetype},
        mark = 'nlc',
        complete_pattern = escape(trigger_chars),
        on_complete = 'ncm2#on_complete#lsp'
    }
    vim.api.nvim_call_function('ncm2#register_source', {source})
end

return {
    on_complete_lsp = on_complete_lsp,
    register_lsp_source = register_lsp_source
}
