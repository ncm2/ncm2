local function on_completion_result(context, err, _, result)
    if err or not result then
        return
    end

    local matches = vim.lsp.util.text_document_completion_list_to_complete_items(result, context.base)
    vim.api.nvim_call_function('ncm2#complete', {context, context.startccol, matches})
end

local function on_complete_lsp(context)
    vim.lsp.buf_request(
        context.bufnr,
        'textDocument/completion',
        vim.lsp.util.make_position_params(),
        function(err, result, _)
            on_completion_result(context, err, _, result)
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
